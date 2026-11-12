"""HTTP acotado; sin redirects, sin retries de escrituras y sin URLs en errores.

El cliente se comparte en todo el proceso para reutilizar conexiones TLS. Cerrarlo es
responsabilidad del ciclo de vida de la aplicación (`close_client`), no de cada petición.
"""
import asyncio
import json
import time
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .config import settings
from .errors import IntegrationError
from .security import assert_safe_endpoint

RETRYABLE_STATUS = {429, 502, 503, 504}
_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


def bounded_timeout(value: Any) -> float:
    """Un catálogo confiable puede acortar o alargar el tiempo, nunca quitar el límite."""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return settings.request_timeout_seconds
    return max(0.5, min(seconds, 120.0))


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        async with _client_lock:
            if _client is None or _client.is_closed:
                _client = httpx.AsyncClient(
                    timeout=settings.request_timeout_seconds,
                    follow_redirects=False,
                    trust_env=False,
                    limits=httpx.Limits(
                        max_connections=settings.http_max_connections,
                        max_keepalive_connections=settings.http_max_keepalive_connections,
                        keepalive_expiry=settings.http_keepalive_expiry_seconds,
                    ),
                )
    return _client


async def close_client() -> None:
    """Cierra el pool. Idempotente: puede llamarse sin que exista un cliente abierto."""
    global _client
    client, _client = _client, None
    if client is not None and not client.is_closed:
        await client.aclose()


def retry_delay(value: str | None, attempt: int) -> float:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - time.time()
        except (TypeError, ValueError, OverflowError):
            seconds = 0.25 * 2**attempt
    return max(0, min(seconds, 10))


async def request(method: str, url: str, allowed_hosts: list[str], *, timeout: Any = None, **kwargs) -> tuple[int, Any]:
    await asyncio.to_thread(assert_safe_endpoint, url, allowed_hosts)
    attempts = 3 if method.upper() in {"GET", "HEAD"} else 1
    client = await get_client()
    deadline = bounded_timeout(timeout) if timeout is not None else settings.request_timeout_seconds
    for attempt in range(attempts):
        try:
            async with client.stream(method, url, timeout=deadline, **kwargs) as res:
                if res.status_code in RETRYABLE_STATUS and attempt + 1 < attempts:
                    await asyncio.sleep(retry_delay(res.headers.get("retry-after"), attempt))
                    continue
                if res.status_code >= 300:
                    raise IntegrationError(f"UPSTREAM_HTTP_{res.status_code}", res.status_code)
                parts, length = [], 0
                async for part in res.aiter_bytes():
                    length += len(part)
                    if length > settings.max_response_bytes:
                        raise IntegrationError("UPSTREAM_RESPONSE_TOO_LARGE")
                    parts.append(part)
                raw = b"".join(parts)
                if not raw:
                    return res.status_code, {"accepted": True}
                if "json" in res.headers.get("content-type", ""):
                    return res.status_code, json.loads(raw)
                return res.status_code, raw.decode("utf-8", errors="replace")
        except httpx.TransportError as exc:
            if attempt + 1 == attempts:
                raise IntegrationError("NETWORK_OUTCOME_UNKNOWN" if attempts == 1 else "NETWORK_ERROR") from exc
            await asyncio.sleep(0.25 * 2**attempt)
    raise IntegrationError("NETWORK_ERROR")
