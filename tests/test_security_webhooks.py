import hashlib
import hmac
import json
import socket

import pytest

from universal_api_orchestrator.config import settings
from universal_api_orchestrator.errors import IntegrationError
from universal_api_orchestrator.security import assert_safe_endpoint, safe_caller_headers
from universal_api_orchestrator.webhooks import extract_events, verify_signature


@pytest.mark.parametrize("url,hosts",[("https://other.com",["example.com"]),("file:///etc/passwd",["example.com"]),("https://user:pass@example.com",["example.com"]),("http://example.com",["example.com"]),("https://example.com",[])])
def test_unsafe_endpoints_fail_closed(url,hosts,monkeypatch):
    monkeypatch.setattr(settings,"allow_private_networks",False)
    with pytest.raises(IntegrationError):
        assert_safe_endpoint(url,hosts)

@pytest.mark.parametrize("ip",["127.0.0.1","10.0.0.1","169.254.169.254","::1","0.0.0.0"])
def test_private_networks_rejected(ip,monkeypatch):
    monkeypatch.setattr(socket,"getaddrinfo",lambda *args:[(0,0,0,"",(ip,443))])
    monkeypatch.setattr(settings,"allow_private_networks",False)
    with pytest.raises(IntegrationError,match="PRIVATE_NETWORK"):
        assert_safe_endpoint("https://example.com",["example.com"])

def test_dns_resolution_failure_is_not_bypass(monkeypatch):
    def fail(*args):
        raise socket.gaierror()
    monkeypatch.setattr(socket,"getaddrinfo",fail)
    with pytest.raises(IntegrationError,match="DNS_UNRESOLVED"):
        assert_safe_endpoint("https://example.com",["example.com"])

def test_caller_cannot_replace_auth_or_host():
    with pytest.raises(IntegrationError):
        safe_caller_headers({"Authorization":"evil"},["Authorization"])
    assert safe_caller_headers({"Accept-Language":"es"},["accept-language"])

@pytest.mark.parametrize("kind",["meta","github"])
def test_valid_and_tampered_hmac(kind):
    raw=b'{"id":"1"}'
    signature="sha256="+hmac.new(b"secret",raw,hashlib.sha256).hexdigest()
    assert verify_signature(kind,"secret",raw,{"x-hub-signature-256":signature})
    assert not verify_signature(kind,"secret",raw+b" ",{"x-hub-signature-256":signature})
    assert not verify_signature(kind,"",raw,{})

def test_slack_replay_window():
    raw=b'{"event_id":"1"}'
    signature="v0="+hmac.new(b"secret",b"v0:1000:"+raw,hashlib.sha256).hexdigest()
    headers={"x-slack-request-timestamp":"1000","x-slack-signature":signature}
    assert verify_signature("slack","secret",raw,headers,now=1050)
    assert not verify_signature("slack","secret",raw,headers,now=1400)

def test_telegram_secret():
    assert verify_signature("telegram","abc",b"{}",{"x-telegram-bot-api-secret-token":"abc"})
    assert not verify_signature("telegram","abc",b"{}",{})

def test_meta_multiple_events_and_delivery_statuses():
    payload={"entry":[{"changes":[{"value":{"messages":[{"id":"m1"},{"id":"m2"}],"statuses":[{"id":"m1","status":"delivered","timestamp":"1"}]}}]}]}
    events=extract_events("meta",payload,json.dumps(payload).encode(),{})
    assert len(events)==3
    assert len({key for key,_ in events})==3
