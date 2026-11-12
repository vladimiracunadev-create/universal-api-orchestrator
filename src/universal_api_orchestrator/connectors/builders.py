"""Construye peticiones reales. No ejecuta red ni lee archivos aportados por un cliente."""
import base64
import re
from dataclasses import dataclass, field
from email import policy
from email.message import EmailMessage
from typing import Any
from urllib.parse import quote

from ..errors import IntegrationError


@dataclass
class RequestSpec:
    method: str
    path: str
    kwargs: dict[str, Any] = field(default_factory=dict)

def path_value(value):
    value = str(value)
    if value in {".", ".."} or not value:
        raise IntegrationError("INVALID_PATH_PARAMETER")
    return quote(value,safe="")

def route(template, params):
    return re.sub(r"\{([A-Za-z0-9_]+)\}",lambda m: path_value(params[m[1]]),template)

def expand(value, params):
    """@nombre sustituye un valor completo sin eval ni ejecución de plantillas."""
    if isinstance(value,str) and value.startswith("@"):
        return params[value[1:]]
    if isinstance(value,dict):
        return {k:expand(v,params) for k,v in value.items()}
    if isinstance(value,list):
        return [expand(v,params) for v in value]
    return value

def generic(cfg, op, params):
    method = op.get("method","GET")
    path = route(op.get("path",""),params)
    kwargs = {}
    if "query_template" in op:
        kwargs["params"] = expand(op["query_template"],params)
    if "body_template" in op:
        kwargs["json"] = expand(op["body_template"],params)
    if "form_template" in op:
        kwargs["data"] = expand(op["form_template"],params)
    if not any(k in op for k in ["query_template","body_template","form_template"]):
        remaining = {k:v for k,v in params.items() if "{"+k+"}" not in op.get("path","")}
        kwargs["params" if method in {"GET","HEAD","DELETE"} else "json"] = remaining
    if cfg.get("provider")=="discord" and "json" in kwargs and not kwargs["json"].get("message_reference"):
        kwargs["json"].pop("message_reference",None)
    if op.get("timeout_seconds") is not None:
        kwargs["timeout"]=op["timeout_seconds"]
    return RequestSpec(method,path,kwargs)

def mime_message(p):
    msg = EmailMessage(policy=policy.SMTP)
    for param, header in [("to","To"),("from","From"),("subject","Subject"),("cc","Cc"),("bcc","Bcc"),("in_reply_to","In-Reply-To"),("references","References")]:
        if p.get(param):
            msg[header] = p[param]  # EmailMessage rechaza inyección CR/LF en cabeceras.
    msg.set_content(p.get("text",""))
    if p.get("html"):
        msg.add_alternative(p["html"],subtype="html")
    total = 0
    for attachment in p.get("attachments",[]):
        raw = base64.b64decode(attachment["data_base64"],validate=True)
        total += len(raw)
        if total > 512000:
            raise IntegrationError("ATTACHMENTS_TOO_LARGE")
        mime = attachment.get("content_type","application/octet-stream").split("/",1)
        if len(mime) != 2:
            raise IntegrationError("INVALID_CONTENT_TYPE")
        msg.add_attachment(raw,maintype=mime[0],subtype=mime[1],filename=attachment["filename"])
    result = {"raw":base64.urlsafe_b64encode(msg.as_bytes()).decode()}
    if p.get("thread_id"):
        result["threadId"] = p["thread_id"]
    return result

def gmail(cfg, op, p):
    action = op.get("action")
    if action in {"send_message","reply_message","create_draft"}:
        body = mime_message(p)
        if action == "create_draft":
            return RequestSpec("POST","/users/me/drafts",{"json":{"message":body}})
        return RequestSpec("POST","/users/me/messages/send",{"json":body})
    return generic(cfg,op,p)

def whatsapp(cfg, op, p):
    action = op.get("action")
    phone = path_value(cfg["phone_number_id"])
    if action == "upload_media":
        raw = base64.b64decode(p["data_base64"],validate=True)
        if len(raw)>512000:
            raise IntegrationError("MEDIA_TOO_LARGE")
        return RequestSpec("POST",f"/{phone}/media",{"data":{"messaging_product":"whatsapp","type":p["content_type"]},"files":{"file":(p["filename"],raw,p["content_type"])}})
    if action == "mark_read":
        body = {"messaging_product":"whatsapp","status":"read","message_id":p["message_id"]}
    elif action in {"send_text","send_template","send_media","send_interactive"}:
        body = {"messaging_product":"whatsapp","recipient_type":"individual","to":p["to"]}
        if p.get("reply_to"):
            body["context"] = {"message_id":p["reply_to"]}
        if action == "send_text":
            body.update(type="text",text={"body":p["text"],"preview_url":p.get("preview_url",False)})
        elif action == "send_template":
            body.update(type="template",template={"name":p["template_name"],"language":{"code":p["language"]},"components":p.get("components",[])})
        elif action == "send_interactive":
            body.update(type="interactive",interactive=p["interactive"])
        else:
            kind=p["media_type"]
            body["type"]=kind
            body[kind]=p["media"]
        return RequestSpec("POST",f"/{phone}/messages",{"json":body})
    else:
        return generic(cfg,op,p)
    return RequestSpec("POST",f"/{phone}/messages",{"json":body})

def outlook(cfg,op,p):
    if op.get("action") in {"send_mail","create_draft"}:
        def recipients(value):
            return [{"emailAddress":{"address":address}} for address in value]
        message = {"subject":p["subject"],"body":{"contentType":p.get("content_type","Text"),"content":p["body"]},"toRecipients":recipients(p["to"])}
        for key in ["cc","bcc"]:
            if p.get(key):
                message[key+"Recipients"]=recipients(p[key])
        if p.get("attachments"):
            if sum(len(base64.b64decode(a["data_base64"],validate=True)) for a in p["attachments"]) > 512000:
                raise IntegrationError("ATTACHMENTS_TOO_LARGE")
            message["attachments"]=[{"@odata.type":"#microsoft.graph.fileAttachment","name":a["filename"],"contentType":a.get("content_type","application/octet-stream"),"contentBytes":a["data_base64"]} for a in p["attachments"]]
        if op["action"] == "send_mail":
            return RequestSpec("POST","/me/sendMail",{"json":{"message":message,"saveToSentItems":True}})
        return RequestSpec("POST","/me/messages",{"json":message})
    return generic(cfg,op,p)

BUILDERS = {"gmail":gmail,"whatsapp":whatsapp,"outlook":outlook}
def build_request(cfg,op,params):
    return BUILDERS.get(cfg.get("provider"),generic)(cfg,op,params)
