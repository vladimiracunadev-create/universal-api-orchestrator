import hashlib
import hmac

import pytest
import yaml
from fastapi.testclient import TestClient

from universal_api_orchestrator.config import settings
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.main import create_app
from universal_api_orchestrator.models import BatchRequest
from universal_api_orchestrator.orchestrator import Orchestrator
from universal_api_orchestrator.registry import SystemRegistry
from universal_api_orchestrator.response_engine import compose_answer


@pytest.fixture
def registry(tmp_path):
    path=tmp_path/"systems.yaml"
    path.write_text(yaml.safe_dump({"systems":{"test":{"protocol":"rest","base_url":"https://example.com","allowed_hosts":["example.com"],"operations":{"read":{"method":"GET","path":"/","effect":"read"},"write":{"method":"POST","path":"/","effect":"write"}}}}}))
    return SystemRegistry(str(path))

async def test_write_requires_all_gates_and_replay(store,registry,monkeypatch):
    calls=[]
    async def execute(*args):
        calls.append(args)
        return 200,{"id":"message-1"}
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute",execute)
    engine=Orchestrator(registry,store)
    monkeypatch.setattr(settings,"allow_writes",False)
    r=await engine.execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True)
    assert not r.ok and not calls
    monkeypatch.setattr(settings,"allow_writes",True)
    r=await engine.execute("test","write",{},confirmed=False,idempotency_key="key-1",approved=True)
    assert not r.ok and not calls
    r=await engine.execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True)
    assert r.ok and len(calls)==1
    r=await engine.execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True)
    assert r.ok and r.meta["idempotent_replay"] and len(calls)==1

async def test_ask_readonly_cannot_write(store,registry,monkeypatch):
    monkeypatch.setattr(settings,"allow_writes",True)
    r=await Orchestrator(registry,store).execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True,read_only=True)
    assert r.error=="ASK_IS_READ_ONLY"

async def test_unknown_delivery_not_automatically_replayed(store,registry,monkeypatch):
    async def fail(*args):
        raise IntegrationError("NETWORK_OUTCOME_UNKNOWN")
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute",fail)
    monkeypatch.setattr(settings,"allow_writes",True)
    engine=Orchestrator(registry,store)
    r=await engine.execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True)
    assert r.meta["requires_reconciliation"]
    r=await engine.execute("test","write",{},confirmed=True,idempotency_key="key-1",approved=True)
    assert r.error=="OUTCOME_PENDING_OR_UNKNOWN_RECONCILE"

def test_duplicate_aliases_fail():
    with pytest.raises(ValueError):
        BatchRequest(requests=[{"system":"a","operation":"b","alias":"x"},{"system":"a","operation":"b","alias":"x"}])

def test_http_health_auth_catalog_and_size_limit(app_settings,monkeypatch):
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code==200
        assert client.get("/v1/systems").status_code==401
        result=client.get("/v1/systems",headers={"X-API-Key":"g"*32})
        assert result.status_code==200
        assert "gmail" in result.json()
        assert "WHATSAPP_ACCESS_TOKEN" not in result.text
        monkeypatch.setattr(settings,"max_request_bytes",10)
        assert client.post("/v1/execute",content=b"x"*11).status_code==413

def test_http_roundtrip_and_openapi(app_settings,monkeypatch):
    async def execute(*args):
        return 200,{"id":1,"title":"title","body":"body"}
    monkeypatch.setattr("universal_api_orchestrator.adapters.rest.RestAdapter.execute",execute)
    with TestClient(create_app()) as client:
        result=client.post("/v1/execute",json={"system":"jsonplaceholder","operation":"get_post","params":{"id":1}},headers={"X-API-Key":"g"*32})
        assert result.json()["data"]["id"]==1
        assert "/v1/ask" in client.get("/openapi.json").json()["paths"]

def test_http_webhook_signature_duplicate_and_ack(app_settings,monkeypatch):
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID","123")
    monkeypatch.setenv("WHATSAPP_GRAPH_VERSION","v23.0")
    monkeypatch.setenv("WHATSAPP_APP_SECRET","secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN","challenge-secret")
    with TestClient(create_app()) as client:
        client.app.state.registry._systems["whatsapp"]["enabled"]=True
        challenge=client.get("/v1/webhooks/whatsapp",params={"hub.mode":"subscribe","hub.verify_token":"challenge-secret","hub.challenge":"987"})
        assert challenge.text=="987"
        raw=b'{"entry":[{"changes":[{"value":{"messages":[{"id":"m1","text":{"body":"private"}}]}}]}]}'
        assert client.post("/v1/webhooks/whatsapp",content=raw).status_code==401
        signature="sha256="+hmac.new(b"secret",raw,hashlib.sha256).hexdigest()
        headers={"X-Hub-Signature-256":signature,"Content-Type":"application/json"}
        assert client.post("/v1/webhooks/whatsapp",content=raw,headers=headers).json()["new_events"]==1
        assert client.post("/v1/webhooks/whatsapp",content=raw,headers=headers).json()["duplicates"]==1
        events=client.get("/v1/events",headers={"X-API-Key":"g"*32}).json()["events"]
        assert len(events)==1
        assert client.post(f"/v1/events/{events[0]['id']}/ack",headers={"X-API-Key":"g"*32}).status_code==403
        assert client.post(f"/v1/events/{events[0]['id']}/ack",headers={"X-API-Key":"g"*32,"X-Approval-Key":"a"*32}).json()["ok"]

async def test_sensitive_data_not_sent_to_llm(monkeypatch):
    monkeypatch.setattr(settings,"ai_mode","openai_compatible")
    monkeypatch.setattr(settings,"ai_allow_sensitive_data",False)
    results={"mail":{"ok":True,"system":"gmail","operation":"get_message","data":{"body":"private"},"meta":{"sensitive":True}}}
    result=await compose_answer("resume",results)
    assert result["mode"]=="deterministic"
    assert "AI_SENSITIVE_DATA_BLOCKED" in result["warnings"]
    assert result["sent"] is False
