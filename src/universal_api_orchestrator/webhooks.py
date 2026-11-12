"""Verificación de origen antes de aceptar y persistir eventos. No envía respuestas externas."""
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

router=APIRouter()

def verify_signature(kind,secret,raw,headers,now=None):
    if not secret:
        return False
    if kind=="telegram":
        return hmac.compare_digest(secret,headers.get("x-telegram-bot-api-secret-token",""))
    if kind=="slack":
        timestamp=headers.get("x-slack-request-timestamp","")
        try:
            if abs((now or time.time())-int(timestamp))>300:
                return False
        except ValueError:
            return False
        expected="v0="+hmac.new(secret.encode(),b"v0:"+timestamp.encode()+b":"+raw,hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,headers.get("x-slack-signature",""))
    if kind in {"meta","github"}:
        expected="sha256="+hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected,headers.get("x-hub-signature-256",""))
    return False

def extract_events(kind,payload,raw,headers):
    fallback=hashlib.sha256(raw).hexdigest()
    if kind=="meta":
        events=[]
        for entry in payload.get("entry",[]):
            for change in entry.get("changes",[]):
                value=change.get("value",{})
                for message in value.get("messages",[]):
                    events.append(("message:"+message["id"],{"kind":"message","message":message,"metadata":value.get("metadata",{}),"contacts":value.get("contacts",[])}))
                for status in value.get("statuses",[]):
                    events.append(("status:"+status["id"]+":"+status.get("status","")+":"+str(status.get("timestamp","")),{"kind":"status","status":status,"metadata":value.get("metadata",{})}))
        return events or [(fallback,payload)]
    if kind=="telegram":
        return [(str(payload.get("update_id",fallback)),payload)]
    if kind=="slack":
        return [(str(payload.get("event_id",fallback)),payload)]
    # No usar solo una cabecera no firmada como identidad: hash firmado incluido.
    return [(headers.get("x-github-delivery","")+":"+fallback,payload)]

def webhook_config(request,system):
    try:
        cfg=request.app.state.registry.get_system(system)
        return cfg["webhook"]
    except (ValueError,KeyError):
        raise HTTPException(404,"WEBHOOK_NOT_CONFIGURED") from None

@router.get("/v1/webhooks/{system}")
async def challenge(system:str,request:Request):
    cfg=webhook_config(request,system)
    expected=os.getenv(cfg.get("verify_token_env",""),"")
    q=request.query_params
    if cfg["type"]!="meta" or not expected or q.get("hub.mode")!="subscribe" or not hmac.compare_digest(expected,q.get("hub.verify_token","")):
        raise HTTPException(401,"INVALID_VERIFICATION_TOKEN")
    return PlainTextResponse(q.get("hub.challenge",""))

@router.post("/v1/webhooks/{system}")
async def receive(system:str,request:Request):
    cfg=webhook_config(request,system)
    raw=await request.body()
    if not verify_signature(cfg["type"],os.getenv(cfg["secret_env"],""),raw,request.headers):
        raise HTTPException(401,"INVALID_WEBHOOK_SIGNATURE")
    try:
        payload=json.loads(raw)
        if not isinstance(payload,dict):
            raise ValueError()
        if cfg["type"]=="slack" and payload.get("type")=="url_verification":
            return {"challenge":payload["challenge"]}
        events=extract_events(cfg["type"],payload,raw,request.headers)
    except (ValueError,KeyError,TypeError):
        raise HTTPException(400,"INVALID_EVENT") from None
    accepted=sum(request.app.state.store.event_add(system,key,event) for key,event in events)
    return {"ok":True,"received":len(events),"new_events":accepted,"duplicates":len(events)-accepted}
