import httpx
import pytest

from universal_api_orchestrator import transport
from universal_api_orchestrator.config import settings
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.transport import close_client, request, retry_delay


@pytest.fixture
def mock_http(monkeypatch):
    """Instala un cliente simulado en el pool compartido y lo retira al terminar."""
    monkeypatch.setattr("universal_api_orchestrator.transport.assert_safe_endpoint", lambda *args: None)

    def install(handler):
        monkeypatch.setattr(transport, "_client", httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False))
    yield install
    monkeypatch.setattr(transport, "_client", None)


async def test_read_retries_respects_retry_after(mock_http):
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(503, headers={"retry-after": "0"}) if len(seen) < 3 else httpx.Response(200, json={"ok": True})
    mock_http(handler)
    code, result = await request("GET", "https://example.com", ["example.com"])
    assert code == 200 and result["ok"] and len(seen) == 3


async def test_write_does_not_retry(mock_http):
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(503)
    mock_http(handler)
    with pytest.raises(IntegrationError):
        await request("POST", "https://example.com", ["example.com"], json={})
    assert len(seen) == 1


async def test_redirects_rejected(mock_http):
    mock_http(lambda req: httpx.Response(302, headers={"Location": "http://169.254.169.254"}))
    with pytest.raises(IntegrationError, match="UPSTREAM_HTTP_302"):
        await request("GET", "https://example.com", ["example.com"])


async def test_response_limit(mock_http, monkeypatch):
    monkeypatch.setattr(settings, "max_response_bytes", 10)
    mock_http(lambda req: httpx.Response(200, content=b"x" * 11))
    with pytest.raises(IntegrationError, match="TOO_LARGE"):
        await request("GET", "https://example.com", ["example.com"])


async def test_operation_timeout_is_bounded_and_forwarded(mock_http):
    seen = []

    def handler(req):
        seen.append(req.extensions.get("timeout", {}))
        return httpx.Response(200, json={"ok": True})
    mock_http(handler)
    await request("GET", "https://example.com", ["example.com"], timeout=7)
    await request("GET", "https://example.com", ["example.com"], timeout=9999)
    await request("GET", "https://example.com", ["example.com"], timeout="no-es-un-numero")
    assert seen[0]["read"] == 7
    assert seen[1]["read"] == 120
    assert seen[2]["read"] == settings.request_timeout_seconds


async def test_client_is_reused_and_closed():
    await close_client()
    first = await transport.get_client()
    second = await transport.get_client()
    assert first is second and not first.is_closed
    await close_client()
    assert first.is_closed
    assert transport._client is None
    await close_client()


def test_retry_after_bounded():
    assert retry_delay("9999", 0) == 10
    assert retry_delay("-3", 0) == 0
