"""Una escritura en duda no se reintenta sola: se inspecciona y se libera a mano."""
import pytest
import yaml
from fastapi.testclient import TestClient

from universal_api_orchestrator.config import settings
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.main import create_app
from universal_api_orchestrator.orchestrator import Orchestrator
from universal_api_orchestrator.registry import SystemRegistry

GATEWAY = {"X-API-Key": "g" * 32}
APPROVED = {"X-API-Key": "g" * 32, "X-Approval-Key": "a" * 32}


@pytest.fixture
def registry(tmp_path):
    path = tmp_path / "systems.yaml"
    path.write_text(yaml.safe_dump({"systems": {"test": {"protocol": "rest", "base_url": "https://example.com", "allowed_hosts": ["example.com"], "operations": {
        "read": {"method": "GET", "path": "/", "effect": "read"},
        "write": {"method": "POST", "path": "/", "effect": "write"},
    }}}}), encoding="utf-8")
    return SystemRegistry(str(path))


async def stuck_write(store, registry, monkeypatch):
    async def fail(*args):
        raise IntegrationError("NETWORK_OUTCOME_UNKNOWN")
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute", fail)
    monkeypatch.setattr(settings, "allow_writes", True)
    engine = Orchestrator(registry, store)
    return await engine.execute("test", "write", {}, confirmed=True, idempotency_key="key-1", approved=True)


async def test_pending_exposes_attempt_without_payload(store, registry, monkeypatch):
    response = await stuck_write(store, registry, monkeypatch)
    assert response.meta["requires_reconciliation"]
    pending = store.pending()
    assert len(pending) == 1
    assert pending[0]["id"] == response.meta["reservation_id"]
    assert pending[0]["system"] == "test" and pending[0]["operation"] == "write"
    assert pending[0]["age_seconds"] >= 0


async def test_release_allows_a_deliberate_retry(store, registry, monkeypatch):
    response = await stuck_write(store, registry, monkeypatch)
    reservation = response.meta["reservation_id"]
    assert store.release(reservation) is True
    assert store.release(reservation) is False
    assert store.pending() == []

    async def ok(*args):
        return 200, {"id": "message-1"}
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute", ok)
    retry = await Orchestrator(registry, store).execute("test", "write", {}, confirmed=True, idempotency_key="key-1", approved=True)
    assert retry.ok


async def test_release_never_touches_completed_reservations(store, registry, monkeypatch):
    async def ok(*args):
        return 200, {"id": "message-1"}
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute", ok)
    monkeypatch.setattr(settings, "allow_writes", True)
    await Orchestrator(registry, store).execute("test", "write", {}, confirmed=True, idempotency_key="key-1", approved=True)
    assert store.release(store.digest("test:key-1")) is False
    assert store.stats()["requests_complete"] == 1


def test_http_reconciliation_requires_approval_and_explicit_outcome(app_settings):
    with TestClient(create_app()) as client:
        client.app.state.store.reserve("test:key-1", {"system": "test", "operation": "write"})
        reservation = client.app.state.store.digest("test:key-1")
        listed = client.get("/v1/reconciliation", headers=GATEWAY)
        assert listed.status_code == 200 and listed.json()["pending"][0]["id"] == reservation
        body = {"confirmed": True, "verified_outcome": "not_delivered"}
        assert client.post(f"/v1/reconciliation/{reservation}/release", json=body, headers=GATEWAY).status_code == 403
        assert client.post(f"/v1/reconciliation/{reservation}/release", json={"confirmed": False, "verified_outcome": "not_delivered"}, headers=APPROVED).status_code == 403
        assert client.post("/v1/reconciliation/no-es-un-id/release", json=body, headers=APPROVED).status_code == 400
        kept = client.post(f"/v1/reconciliation/{reservation}/release", json={"confirmed": True, "verified_outcome": "delivered_do_not_retry"}, headers=APPROVED)
        assert kept.status_code == 409
        assert client.app.state.store.pending()
        released = client.post(f"/v1/reconciliation/{reservation}/release", json=body, headers=APPROVED)
        assert released.json() == {"released": True, "verified_outcome": "not_delivered", "retry_is_manual": True}
        assert client.post(f"/v1/reconciliation/{reservation}/release", json=body, headers=APPROVED).status_code == 404


def test_prune_keeps_pending_reservations(store):
    store.reserve("test:key-1", {"system": "test"})
    store.reserve("test:key-2", {"system": "test"})
    store.complete("test:key-2", {"ok": True, "system": "test", "operation": "write", "protocol": "rest", "meta": {}})
    assert store.prune_requests(days=0) == 1
    assert [item["id"] for item in store.pending()] == [store.digest("test:key-1")]
