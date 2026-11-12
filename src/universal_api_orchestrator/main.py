"""Servidor. No lee cuentas ni envía mensajes al arrancar."""
import hmac
import re
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from . import __version__
from .config import settings
from .models import AskRequest, BatchRequest, ExecuteRequest, ReleaseRequest
from .orchestrator import Orchestrator
from .ratelimit import RateLimiter
from .registry import SystemRegistry
from .response_engine import compose_answer
from .store import Store
from .transport import close_client
from .webhooks import router

SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")
RESERVATION_ID = re.compile(r"^[0-9a-f]{64}$")
VERIFIED_OUTCOMES = {"not_delivered", "delivered_duplicate_acceptable", "delivered_do_not_retry"}


async def authorize(x_api_key: str = Header(default="")):
    if len(settings.gateway_api_key) < 24:
        raise HTTPException(503, "GATEWAY_KEY_NOT_CONFIGURED")
    if not hmac.compare_digest(x_api_key, settings.gateway_api_key):
        raise HTTPException(401, "INVALID_API_KEY")


def approved(key):
    return len(settings.approval_api_key) >= 24 and hmac.compare_digest(key, settings.approval_api_key)


async def require_approval(x_approval_key: str = Header(default="")):
    if not approved(x_approval_key):
        raise HTTPException(403, "APPROVAL_REQUIRED")


def create_app():
    @asynccontextmanager
    async def lifespan(app):
        app.state.registry = SystemRegistry(settings.systems_config)
        app.state.store = Store(settings.state_db, settings.state_key)
        app.state.orchestrator = Orchestrator(app.state.registry, app.state.store)
        app.state.limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_burst)
        try:
            yield
        finally:
            # Devuelve las conexiones del pool; no reintenta ni vacía el estado local.
            await close_client()

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan, description="Conectores multicanal. Consultar no autoriza enviar. X-API-Key obligatoria.")

    @app.middleware("http")
    async def body_limit(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if SAFE_REQUEST_ID.match(incoming) else str(uuid.uuid4())
        size, parts = 0, []
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.max_request_bytes:
                return JSONResponse({"detail": "REQUEST_TOO_LARGE", "request_id": request_id}, status_code=413, headers={"X-Request-Id": request_id})
            parts.append(chunk)
        request._body = b"".join(parts)
        limiter = getattr(request.app.state, "limiter", None)
        if limiter is not None and request.url.path != "/health":
            identity = limiter.identity(request.headers.get("x-api-key", ""), request.client.host if request.client else "unknown")
            allowed, remaining, wait = limiter.check(identity)
            if not allowed:
                return JSONResponse(
                    {"detail": "RATE_LIMIT_EXCEEDED", "request_id": request_id},
                    status_code=429,
                    headers={"Retry-After": str(max(1, int(wait) + 1)), "X-Request-Id": request_id, "X-RateLimit-Remaining": "0"},
                )
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Request-Id"] = request_id
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": __version__}

    @app.get("/v1/systems", dependencies=[Depends(authorize)])
    async def systems(request: Request):
        return request.app.state.registry.list_public()

    @app.get("/v1/systems/{system}", dependencies=[Depends(authorize)])
    async def system_detail(system: str, request: Request):
        try:
            return request.app.state.registry.public_system(system)
        except KeyError:
            raise HTTPException(404, "SYSTEM_NOT_FOUND") from None

    @app.post("/v1/execute", dependencies=[Depends(authorize)])
    async def execute(body: ExecuteRequest, request: Request, x_approval_key: str = Header(default="")):
        return await request.app.state.orchestrator.execute(body.system, body.operation, body.params, body.headers, confirmed=body.confirmed, idempotency_key=body.idempotency_key, approved=approved(x_approval_key))

    @app.post("/v1/batch", dependencies=[Depends(authorize)])
    async def batch(body: BatchRequest, request: Request, x_approval_key: str = Header(default="")):
        return await request.app.state.orchestrator.batch(body.requests, body.fail_fast, approved=approved(x_approval_key))

    @app.post("/v1/ask", dependencies=[Depends(authorize)])
    async def ask(body: AskRequest, request: Request):
        results = await request.app.state.orchestrator.batch(body.requests, body.fail_fast, read_only=True)
        return await compose_answer(body.question, results, body.response_template)

    @app.get("/v1/events", dependencies=[Depends(authorize)])
    async def events(request: Request, limit: int = Query(50, ge=1, le=100), after: int = Query(0, ge=0)):
        return {"events": request.app.state.store.events(limit, after)}

    @app.post("/v1/events/{event_id}/ack", dependencies=[Depends(authorize)])
    async def ack(event_id: int, request: Request, x_approval_key: str = Header(default="")):
        if not approved(x_approval_key):
            raise HTTPException(403, "ACK_APPROVAL_REQUIRED")
        return {"ok": request.app.state.store.ack(event_id)}

    @app.get("/v1/reconciliation", dependencies=[Depends(authorize)])
    async def reconciliation(request: Request, limit: int = Query(50, ge=1, le=200)):
        """Escrituras cuyo resultado real se desconoce. Ninguna se reintenta por su cuenta."""
        return {
            "pending": request.app.state.store.pending(limit),
            "guidance": "Compruebe el resultado en el proveedor antes de liberar la reserva.",
        }

    @app.post("/v1/reconciliation/{reservation_id}/release", dependencies=[Depends(authorize), Depends(require_approval)])
    async def release(reservation_id: str, body: ReleaseRequest, request: Request):
        """Libera la reserva para permitir un reintento deliberado. No contacta al proveedor."""
        if not RESERVATION_ID.match(reservation_id):
            raise HTTPException(400, "INVALID_RESERVATION_ID")
        if not body.confirmed:
            raise HTTPException(403, "RELEASE_CONFIRMATION_REQUIRED")
        if body.verified_outcome not in VERIFIED_OUTCOMES:
            raise HTTPException(422, "UNKNOWN_VERIFIED_OUTCOME")
        if body.verified_outcome == "delivered_do_not_retry":
            raise HTTPException(409, "RESERVATION_KEPT_TO_PREVENT_DUPLICATE")
        released = request.app.state.store.release(reservation_id)
        if not released:
            raise HTTPException(404, "RESERVATION_NOT_FOUND_OR_ALREADY_COMPLETE")
        return {"released": True, "verified_outcome": body.verified_outcome, "retry_is_manual": True}

    @app.get("/v1/stats", dependencies=[Depends(authorize)])
    async def stats(request: Request):
        """Recuentos del estado local. No consulta proveedores ni verifica credenciales."""
        return {
            "version": __version__,
            "allow_writes": settings.allow_writes,
            "ai_mode": settings.ai_mode,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "systems": len(request.app.state.registry.list_public()),
            "state": request.app.state.store.stats(),
        }

    @app.post("/v1/admin/reload", dependencies=[Depends(authorize), Depends(require_approval)])
    async def reload_catalog(request: Request):
        """Relee el catálogo tras `uao enable`. Un catálogo inválido deja el anterior en uso."""
        try:
            loaded = request.app.state.registry.reload()
        except (ValueError, OSError):
            raise HTTPException(422, "INVALID_CATALOG_PREVIOUS_KEPT") from None
        return {"reloaded": True, "systems": loaded}

    app.include_router(router)
    return app


app = create_app()
