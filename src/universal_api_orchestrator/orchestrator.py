"""Aplica políticas antes de autenticación, transporte, normalización o efectos externos."""
import asyncio
import logging
import time
import uuid

from jsonschema import ValidationError, validate

from .adapters import ADAPTERS
from .auth import AuthManager
from .config import settings
from .errors import IntegrationError
from .models import BatchItem, UnifiedResponse
from .normalizer import normalize
from .registry import MissingConfiguration, SystemDisabled
from .security import safe_caller_headers

log = logging.getLogger("uao.audit")


class Orchestrator:
    def __init__(self, registry, store):
        self.registry, self.store = registry, store
        self.auth = AuthManager(store)
        self.semaphore = asyncio.Semaphore(settings.max_concurrency)

    def resolve(self, system_name, operation_name):
        """Traduce fallos de catálogo a códigos estables; no revela rutas ni variables."""
        try:
            system = self.registry.get_system(system_name)
        except KeyError as exc:
            raise IntegrationError("SYSTEM_NOT_FOUND", 404) from exc
        except SystemDisabled as exc:
            raise IntegrationError("SYSTEM_DISABLED", 409) from exc
        except MissingConfiguration as exc:
            raise IntegrationError("SYSTEM_CONFIGURATION_INCOMPLETE", 503) from exc
        operations = system.get("operations", {})
        if operation_name not in operations:
            raise IntegrationError("OPERATION_NOT_FOUND", 404)
        return system, operations[operation_name]

    async def execute(self, system_name, operation_name, params, headers=None, *, confirmed=False, idempotency_key=None, approved=False, read_only=False):
        started = time.perf_counter()
        trace = str(uuid.uuid4())
        protocol = "unknown"
        reserved = False
        storage_key = None
        try:
            system, operation = self.resolve(system_name, operation_name)
            protocol = system["protocol"]
            params = {**operation.get("defaults", {}), **params}
            validate(params, operation.get("input_schema", {"type": "object"}))
            # POST de consulta debe declarar read en configuración confiable.
            effect = operation.get("effect", "read" if operation.get("method", "POST") in {"GET", "HEAD"} else "write")
            outgoing = {**system.get("headers", {}), **operation.get("headers", {}), **safe_caller_headers(headers or {}, system.get("allowed_request_headers", []))}
            if effect != "read":
                if read_only:
                    raise IntegrationError("ASK_IS_READ_ONLY", 403)
                if not settings.allow_writes or not approved or not confirmed:
                    raise IntegrationError("WRITE_APPROVAL_REQUIRED", 403)
                if not idempotency_key:
                    raise IntegrationError("IDEMPOTENCY_KEY_REQUIRED", 400)
            async with self.semaphore:
                # Obtener token antes de reservar: credenciales ausentes no bloquean una clave.
                outgoing.update(await self.auth.headers(system.get("auth", {})))
                if effect != "read":
                    storage_key = f"{system_name}:{idempotency_key}"
                    replay = self.store.reserve(storage_key, {"system": system_name, "operation": operation_name, "params": params, "headers": headers or {}})
                    if replay:
                        replay["meta"]["idempotent_replay"] = True
                        return UnifiedResponse(**replay)
                    reserved = True
                adapter = ADAPTERS.get(protocol)
                if not adapter:
                    raise IntegrationError("UNSUPPORTED_PROTOCOL")
                status, payload = await adapter.execute(system, operation, params, outgoing)
            response = UnifiedResponse(ok=True, system=system_name, operation=operation_name, protocol=protocol, status_code=status, data=normalize(payload, operation.get("response_map")), meta={"trace_id": trace, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "effect": effect, "sensitive": system.get("sensitive", False), "delivery": "provider_accepted_not_delivery_receipt" if effect != "read" else None})
            if reserved:
                self.store.complete(storage_key, response.model_dump())
            log.info("integration trace=%s system=%s operation=%s ok=true", trace, system_name, operation_name)
            return response
        except IntegrationError as exc:
            code, status = exc.code, exc.status
        except ValidationError:
            code, status = "INVALID_INPUT_SCHEMA", 422
        except (KeyError, ValueError):
            code, status = "INVALID_OPERATION_CONFIGURATION_OR_INPUT", 400
        except Exception:
            code, status = "INTEGRATION_FAILURE", None
        log.warning("integration trace=%s system=%s operation=%s code=%s", trace, system_name, operation_name, code)
        # Una escritura fallida después de reservar queda pending/unknown; requiere reconciliación.
        meta = {"trace_id": trace, "elapsed_ms": round((time.perf_counter() - started) * 1000, 2), "requires_reconciliation": reserved}
        if reserved:
            meta["reservation_id"] = self.store.digest(storage_key)
        return UnifiedResponse(ok=False, system=system_name, operation=operation_name, protocol=protocol, status_code=status, error=code, meta=meta)

    async def batch(self, items: list[BatchItem], fail_fast=False, *, approved=False, read_only=False):
        async def run(item):
            return await self.execute(item.system, item.operation, item.params, item.headers, confirmed=item.confirmed, idempotency_key=item.idempotency_key, approved=approved, read_only=read_only)
        if fail_fast:
            result = {}
            for index, item in enumerate(items):
                response = await run(item)
                result[item.alias or f"item_{index}"] = response.model_dump()
                if not response.ok:
                    break
            return result
        responses = await asyncio.gather(*(run(item) for item in items))
        return {(item.alias or f"item_{index}"): response.model_dump() for index, (item, response) in enumerate(zip(items, responses, strict=True))}
