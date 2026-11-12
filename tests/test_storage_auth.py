import asyncio
import time

import pytest

from universal_api_orchestrator.auth import AuthManager
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.store import Store


def test_state_requires_explicit_encryption_key(tmp_path):
    with pytest.raises(ValueError):
        Store(str(tmp_path/"db"),"")

def test_encryption_roundtrip_and_no_plaintext(store):
    store.token_put("google",{"refresh_token":"TOP_SECRET_PERSISTENT_TOKEN"})
    store.event_add("gmail","1",{"body":"PRIVATE_PERSONAL_MESSAGE"})
    assert store.token_get("google")["refresh_token"]=="TOP_SECRET_PERSISTENT_TOKEN"
    with open(store.path,"rb") as f:
        raw=f.read()
    assert b"TOP_SECRET_PERSISTENT_TOKEN" not in raw
    assert b"PRIVATE_PERSONAL_MESSAGE" not in raw

def test_idempotency_pending_conflict_and_replay(store):
    assert store.reserve("key",{"params":{"to":"a"}}) is None
    with pytest.raises(IntegrationError,match="OUTCOME_PENDING"):
        store.reserve("key",{"params":{"to":"a"}})
    with pytest.raises(IntegrationError,match="IDEMPOTENCY_CONFLICT"):
        store.reserve("key",{"params":{"to":"b"}})
    store.complete("key",{"ok":True})
    assert store.reserve("key",{"params":{"to":"a"}})=={"ok":True}

def test_event_dedup_ack_and_pagination(store):
    assert store.event_add("slack","1",{"text":"hello"})
    assert not store.event_add("slack","1",{"text":"hello"})
    assert store.events()[0]["payload"]["text"]=="hello"
    assert store.ack(store.events()[0]["id"])
    assert store.events()==[]

async def test_token_refresh_single_flight_and_rotation(store,monkeypatch):
    store.token_put("google",{"refresh_token":"old","client_id":"cid","client_secret":"sec","expires_at":0})
    calls=[]
    async def send(*args,**kwargs):
        calls.append(kwargs["data"])
        await asyncio.sleep(0)
        return 200,{"access_token":"fresh","refresh_token":"rotated","expires_in":3600}
    monkeypatch.setattr("universal_api_orchestrator.auth.request",send)
    auth=AuthManager(store)
    cfg={"type":"oauth2","token_key":"google","token_url":"https://oauth2.googleapis.com/token","allowed_hosts":["oauth2.googleapis.com"]}
    values=await asyncio.gather(auth.headers(cfg),auth.headers(cfg))
    assert len(calls)==1
    assert values[0]=={"Authorization":"Bearer fresh"}
    assert store.token_get("google")["refresh_token"]=="rotated"

async def test_bearer_missing_and_basic_encoding(store,monkeypatch):
    auth=AuthManager(store)
    with pytest.raises(IntegrationError,match="MISSING_CREDENTIALS"):
        await auth.headers({"type":"bearer","token_env":"ABSENT_EXAMPLE_TOKEN"})
    monkeypatch.setenv("USR","alice");monkeypatch.setenv("PWD","pass")
    result=await auth.headers({"type":"basic","username_env":"USR","password_env":"PWD"})
    assert result["Authorization"]=="Basic YWxpY2U6cGFzcw=="

async def test_cached_oauth_never_calls_network(store,monkeypatch):
    store.token_put("g",{"access_token":"cached","expires_at":time.time()+3600})
    result=await AuthManager(store).headers({"type":"oauth2","token_key":"g"})
    assert result=={"Authorization":"Bearer cached"}
