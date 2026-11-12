"""Control de carga, identidad de petición, errores precisos de catálogo y recarga."""
import pytest
import yaml
from fastapi.testclient import TestClient

from universal_api_orchestrator.config import settings
from universal_api_orchestrator.main import create_app
from universal_api_orchestrator.orchestrator import Orchestrator
from universal_api_orchestrator.ratelimit import RateLimiter
from universal_api_orchestrator.registry import SystemRegistry

GATEWAY = {"X-API-Key": "g" * 32}
APPROVED = {"X-API-Key": "g" * 32, "X-Approval-Key": "a" * 32}


def write_catalog(path, enabled=True, extra_operation=False):
    operations = {"read": {"method": "GET", "path": "/", "effect": "read"}}
    if extra_operation:
        operations["read_more"] = {"method": "GET", "path": "/more", "effect": "read"}
    path.write_text(yaml.safe_dump({"systems": {
        "test": {"protocol": "rest", "base_url": "https://example.com", "allowed_hosts": ["example.com"], "enabled": enabled, "operations": operations},
        "needs_env": {"protocol": "rest", "base_url": "https://example.com", "allowed_hosts": ["example.com"], "headers": {"X-Token": "${UAO_TEST_ABSENT_VARIABLE}"}, "operations": operations},
    }}), encoding="utf-8")


def test_token_bucket_refills_and_never_grows_unbounded():
    limiter = RateLimiter(per_minute=60, burst=2)
    identity = limiter.identity("clave", "127.0.0.1")
    assert limiter.check(identity, now=0)[0] is True
    assert limiter.check(identity, now=0)[0] is True
    allowed, remaining, wait = limiter.check(identity, now=0)
    assert allowed is False and remaining == 0 and wait > 0
    assert limiter.check(identity, now=1.1)[0] is True
    assert RateLimiter(per_minute=0, burst=1).check(identity, now=0)[0] is True
    small = RateLimiter(per_minute=6000, burst=5, max_identities=4)
    for index in range(40):
        small.check(small.identity(f"clave-{index}", "127.0.0.1"), now=index)
    assert len(small.buckets) <= 4


def test_identity_does_not_store_the_api_key():
    limiter = RateLimiter(60, 5)
    identity = limiter.identity("super-secreto", "127.0.0.1")
    assert "super-secreto" not in identity and len(identity) == 32
    assert identity != limiter.identity("", "127.0.0.1")


def test_http_rate_limit_returns_429_with_retry_after(app_settings, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 60)
    monkeypatch.setattr(settings, "rate_limit_burst", 2)
    with TestClient(create_app()) as client:
        assert client.get("/v1/systems", headers=GATEWAY).status_code == 200
        assert client.get("/v1/systems", headers=GATEWAY).status_code == 200
        limited = client.get("/v1/systems", headers=GATEWAY)
        assert limited.status_code == 429
        assert int(limited.headers["Retry-After"]) >= 1
        assert limited.json()["detail"] == "RATE_LIMIT_EXCEEDED"
        # /health queda fuera del control para no romper sondas de contenedor.
        assert client.get("/health").status_code == 200


def test_request_id_is_echoed_and_sanitised(app_settings):
    with TestClient(create_app()) as client:
        generated = client.get("/health")
        assert len(generated.headers["X-Request-Id"]) == 36
        assert generated.headers["Referrer-Policy"] == "no-referrer"
        mine = client.get("/health", headers={"X-Request-Id": "trace-de-cliente-1"})
        assert mine.headers["X-Request-Id"] == "trace-de-cliente-1"
        injected = client.get("/health", headers={"X-Request-Id": "corto"})
        assert injected.headers["X-Request-Id"] != "corto"


async def test_catalog_errors_are_specific(store, tmp_path, monkeypatch):
    path = tmp_path / "systems.yaml"
    write_catalog(path)
    engine = Orchestrator(SystemRegistry(str(path)), store)
    assert (await engine.execute("no_existe", "read", {})).error == "SYSTEM_NOT_FOUND"
    assert (await engine.execute("no_existe", "read", {})).status_code == 404
    assert (await engine.execute("test", "no_existe", {})).error == "OPERATION_NOT_FOUND"
    monkeypatch.delenv("UAO_TEST_ABSENT_VARIABLE", raising=False)
    incomplete = await engine.execute("needs_env", "read", {})
    assert incomplete.error == "SYSTEM_CONFIGURATION_INCOMPLETE" and incomplete.status_code == 503
    write_catalog(path, enabled=False)
    disabled = await Orchestrator(SystemRegistry(str(path)), store).execute("test", "read", {})
    assert disabled.error == "SYSTEM_DISABLED" and disabled.status_code == 409


def test_system_detail_and_stats(app_settings):
    with TestClient(create_app()) as client:
        detail = client.get("/v1/systems/gmail", headers=GATEWAY)
        assert detail.status_code == 200 and detail.json()["provider"] == "gmail"
        assert "GOOGLE" not in detail.text and "${" not in detail.text
        assert client.get("/v1/systems/no_existe", headers=GATEWAY).status_code == 404
        stats = client.get("/v1/stats", headers=GATEWAY)
        assert stats.status_code == 401 or stats.json()["state"]["events_pending"] == 0
        assert stats.json()["allow_writes"] is False
        assert stats.json()["systems"] == 18


def test_reload_requires_approval_and_keeps_previous_catalog(app_settings, tmp_path, monkeypatch):
    path = tmp_path / "systems.yaml"
    write_catalog(path)
    monkeypatch.setattr(settings, "systems_config", str(path))
    with TestClient(create_app()) as client:
        assert client.post("/v1/admin/reload", headers=GATEWAY).status_code == 403
        write_catalog(path, extra_operation=True)
        reloaded = client.post("/v1/admin/reload", headers=APPROVED)
        assert reloaded.json() == {"reloaded": True, "systems": 2}
        assert "read_more" in client.get("/v1/systems/test", headers=GATEWAY).json()["operations"]
        path.write_text("systems: [esto-no-es-un-mapa]", encoding="utf-8")
        assert client.post("/v1/admin/reload", headers=APPROVED).status_code == 422
        assert "read_more" in client.get("/v1/systems/test", headers=GATEWAY).json()["operations"]


def test_registry_reload_rejects_broken_file_in_place(tmp_path):
    path = tmp_path / "systems.yaml"
    write_catalog(path)
    registry = SystemRegistry(str(path))
    path.write_text("systems:\n  test:\n    operations: no-es-un-mapa\n", encoding="utf-8")
    with pytest.raises(ValueError):
        registry.reload()
    assert registry.has("test") and registry.public_system("test")["operations"] == ["read"]
