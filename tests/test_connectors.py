import base64
import json
import re
from copy import deepcopy
from email import policy
from email.parser import BytesParser
from pathlib import Path

import pytest
import yaml
from jsonschema import validate

from universal_api_orchestrator.connectors.builders import build_request, mime_message, route
from universal_api_orchestrator.errors import IntegrationError

SYSTEMS=yaml.safe_load(Path("config/systems.yaml").read_text(encoding="utf-8"))["systems"]
CASES=[(name,key) for name,cfg in SYSTEMS.items() if cfg.get("protocol")=="provider" for key in cfg["operations"]]

def sample(schema):
    if "enum" in schema:
        return schema["enum"][0]
    typ=schema.get("type","object")
    if isinstance(typ,list):
        typ=typ[0]
    if typ=="object":
        return {k:sample(schema["properties"][k]) for k in schema.get("required",[])}
    if typ=="array":
        return [sample(schema.get("items",{})) for _ in range(schema.get("minItems",0))]
    if typ=="integer":
        return max(schema.get("minimum",0),1)
    if typ=="boolean":
        return False
    if "pattern" in schema:
        pattern=schema["pattern"]
        if "https" in pattern:
            return "https://example.com/test"
        if "@" in pattern:
            return "someone@example.com"
        if "[1-9]" in pattern:
            return "56911111111"
    return "x"*max(10,schema.get("minLength",1))

@pytest.mark.parametrize("system,operation",CASES)
def test_every_operation_builds_real_request(system,operation):
    cfg=deepcopy(SYSTEMS[system])
    cfg=json.loads(re.sub(r"\$\{[^}]+\}","123456",json.dumps(cfg)))
    op=cfg["operations"][operation]
    p={**op.get("defaults",{}),**sample(op["input_schema"])}
    if "data_base64" in p:
        p["data_base64"]=base64.b64encode(b"media").decode()
    if operation=="send_media":
        p["media"]={"id":"123456"}
    if operation=="upload_media":
        p["content_type"]="text/plain"
    validate(p,op["input_schema"])
    spec=build_request(cfg,op,p)
    assert spec.method in {"GET","POST","PATCH","DELETE","PUT","HEAD"}
    assert spec.path.startswith("/")
    assert "{" not in spec.path
    assert spec.kwargs is not None

@pytest.mark.parametrize("path",list(Path("examples/requests").glob("*.json")))
def test_examples_obey_declared_input_schema(path):
    body=json.loads(path.read_text(encoding="utf-8"))
    for request in body.get("requests",[body]):
        cfg=SYSTEMS[request["system"]]["operations"][request["operation"]]
        validate(request.get("params",{}),cfg["input_schema"])
        assert not request.get("confirmed",False)

def test_gmail_mime_unicode_attachment_thread():
    p={"to":"reader@example.com","subject":"Información — Ñ","text":"Hola mundo","html":"<p>Hola</p>","thread_id":"t1","in_reply_to":"<id@example.com>","references":"<id@example.com>","attachments":[{"filename":"nota.txt","data_base64":base64.b64encode(b"file-content").decode(),"content_type":"text/plain"}]}
    body=mime_message(p)
    message=BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(body["raw"]))
    assert message["Subject"]==p["subject"]
    assert message["In-Reply-To"]==p["in_reply_to"]
    assert body["threadId"]=="t1"
    assert next(iter(message.iter_attachments())).get_payload(decode=True)==b"file-content"

def test_mime_header_injection_rejected():
    with pytest.raises(ValueError):
        mime_message({"to":"a@example.com\r\nBcc: victim@example.com","text":"body"})

def test_attachment_limit():
    with pytest.raises(IntegrationError,match="ATTACHMENTS_TOO_LARGE"):
        mime_message({"text":"a","attachments":[{"filename":"a.txt","data_base64":base64.b64encode(b"x"*512001).decode()}]})

def test_path_parameters_do_not_inject_routes():
    assert route("/messages/{id}",{"id":"a/b?c=1"})=="/messages/a%2Fb%3Fc%3D1"
    with pytest.raises(IntegrationError):
        route("/messages/{id}",{"id":".."})

def test_whatsapp_template_shape():
    spec=build_request({"provider":"whatsapp","phone_number_id":"123"},{"action":"send_template"},{"to":"56911111111","template_name":"hello_world","language":"en_US"})
    assert spec.path=="/123/messages"
    assert spec.kwargs["json"]["template"]["language"]=={"code":"en_US"}
    assert spec.kwargs["json"]["messaging_product"]=="whatsapp"
