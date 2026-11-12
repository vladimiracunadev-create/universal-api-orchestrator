"""CLI local: configuración, autorización y cliente HTTP sin imprimir secretos."""
import argparse
import json
import os
import sys
import time
from datetime import UTC
from pathlib import Path

import httpx
import yaml

from . import __version__
from .config import settings
from .registry import SystemRegistry
from .store import Store


def dump(value):
    print(json.dumps(value,ensure_ascii=False,indent=2))

def auth_google(args):
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow=InstalledAppFlow.from_client_secrets_file(args.client,scopes=args.scopes,autogenerate_code_verifier=True)
    creds=flow.run_local_server(host="127.0.0.1",port=args.port,open_browser=not args.no_browser,access_type="offline",prompt="consent")
    payload=json.loads(creds.to_json())
    payload["access_token"]=creds.token
    payload["expires_at"]=creds.expiry.replace(tzinfo=UTC).timestamp() if creds.expiry else time.time()+300
    Store(settings.state_db,settings.state_key).token_put(args.token_key,payload)
    print("Credenciales cifradas guardadas. No se han leído ni enviado correos.")

def auth_microsoft(args):
    import msal
    store=Store(settings.state_db,settings.state_key)
    cache=msal.SerializableTokenCache()
    saved=store.token_get(args.token_key)
    if saved:
        cache.deserialize(saved["cache"])
    tenant=os.environ["MICROSOFT_TENANT_ID"]
    client=msal.PublicClientApplication(os.environ["MICROSOFT_CLIENT_ID"],authority=f"https://login.microsoftonline.com/{tenant}",token_cache=cache)
    flow=client.initiate_device_flow(scopes=args.scopes)
    if "user_code" not in flow:
        raise ValueError("No se pudo iniciar device flow; revise registro/tenant.")
    print(flow["message"])
    result=client.acquire_token_by_device_flow(flow)
    if not result.get("access_token"):
        raise ValueError("Consentimiento rechazado o incompleto.")
    store.token_put(args.token_key,{"cache":cache.serialize()})
    print("Caché MSAL cifrada guardada.")

def main():
    p=argparse.ArgumentParser(description="Universal API Orchestrator CLI")
    p.add_argument("--url",default="http://127.0.0.1:8080")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("catalog")
    sub.add_parser("doctor")
    for command in ["enable","disable"]:
        c=sub.add_parser(command);c.add_argument("system")
    for command in ["execute","ask","batch"]:
        c=sub.add_parser(command);c.add_argument("file");c.add_argument("--approve",action="store_true",help="Usar APPROVAL_API_KEY; no modifica confirmed en JSON.")
    a=sub.add_parser("auth-google")
    a.add_argument("--client",required=True);a.add_argument("--token-key",default="google")
    a.add_argument("--scopes",nargs="+",required=True);a.add_argument("--port",type=int,default=8765);a.add_argument("--no-browser",action="store_true")
    a=sub.add_parser("auth-microsoft")
    a.add_argument("--token-key",default="microsoft");a.add_argument("--scopes",nargs="+",required=True)
    sub.add_parser("events")
    a=sub.add_parser("ack");a.add_argument("id",type=int)
    a=sub.add_parser("prune-events");a.add_argument("--days",type=int,default=settings.events_retention_days)
    a=sub.add_parser("prune-requests");a.add_argument("--days",type=int,default=settings.requests_retention_days)
    sub.add_parser("health")
    sub.add_parser("stats")
    sub.add_parser("reload")
    sub.add_parser("pending")
    a=sub.add_parser("release",help="Liberar una reserva en duda tras comprobar el resultado real.")
    a.add_argument("reservation_id")
    a.add_argument("--verified-outcome",required=True,choices=["not_delivered","delivered_duplicate_acceptable","delivered_do_not_retry"])
    a.add_argument("--note",default=None)
    a.add_argument("--confirm",action="store_true",help="Obligatorio: afirma que comprobó el resultado en el proveedor.")
    args=p.parse_args()
    try:
        if args.command=="auth-google":
            return auth_google(args)
        if args.command=="auth-microsoft":
            return auth_microsoft(args)
        if args.command in {"catalog","doctor"}:
            registry=SystemRegistry(settings.systems_config)
            if args.command=="catalog":
                return dump(registry.list_public())
            checks={"version":__version__,"python":sys.version.split()[0],"gateway_key_configured":len(settings.gateway_api_key)>=24,"approval_key_configured":len(settings.approval_api_key)>=24,"state_key_configured":bool(settings.state_key),"allow_writes":settings.allow_writes,"ai_mode":settings.ai_mode,"rate_limit_per_minute":settings.rate_limit_per_minute,"private_networks_allowed":settings.allow_private_networks,"systems":{}}
            for name,cfg in registry.list_public().items():
                try:
                    registry.get_system(name)
                    checks["systems"][name]="config_ready_credentials_not_verified" if cfg["enabled"] else "disabled"
                except (ValueError,KeyError):
                    checks["systems"][name]="disabled" if not cfg["enabled"] else "missing_environment"
            return dump(checks)
        if args.command in {"enable","disable"}:
            path=Path(settings.systems_config)
            raw=yaml.safe_load(path.read_text(encoding="utf-8"))
            raw["systems"][args.system]["enabled"]=args.command=="enable"
            path.write_text(yaml.safe_dump(raw,allow_unicode=True,sort_keys=False),encoding="utf-8")
            print("Configuración actualizada; ejecute uao reload o reinicie el servidor.")
            return
        if args.command in {"prune-events","prune-requests"}:
            if args.days<1:
                raise ValueError("days debe ser positivo")
            store=Store(settings.state_db,settings.state_key)
            if args.command=="prune-events":
                return dump({"deleted_events":store.prune(args.days)})
            return dump({"deleted_completed_reservations":store.prune_requests(args.days)})
        if args.command=="release" and not args.confirm:
            raise ValueError("release requiere --confirm")
        headers={"X-API-Key":settings.gateway_api_key}
        if getattr(args,"approve",False) or args.command in {"ack","release","reload"}:
            headers["X-Approval-Key"]=settings.approval_api_key
        with httpx.Client(base_url=args.url,timeout=90,trust_env=False) as client:
            if args.command=="health":
                response=client.get("/health")
            elif args.command=="events":
                response=client.get("/v1/events",headers=headers)
            elif args.command=="stats":
                response=client.get("/v1/stats",headers=headers)
            elif args.command=="pending":
                response=client.get("/v1/reconciliation",headers=headers)
            elif args.command=="reload":
                response=client.post("/v1/admin/reload",headers=headers)
            elif args.command=="ack":
                response=client.post(f"/v1/events/{args.id}/ack",headers=headers)
            elif args.command=="release":
                body={"confirmed":True,"verified_outcome":args.verified_outcome}
                if args.note:
                    body["note"]=args.note
                response=client.post(f"/v1/reconciliation/{args.reservation_id}/release",json=body,headers=headers)
            else:
                body=json.loads(Path(args.file).read_text(encoding="utf-8"))
                response=client.post(f"/v1/{args.command}",json=body,headers=headers)
            response.raise_for_status()
            result=response.json();dump(result)
            if result.get("ok") is False or result.get("errors"):
                sys.exit(2)
    except (ValueError,KeyError,OSError,ImportError,httpx.HTTPError):
        print("Error: revise archivo, variables, extras instalados y servidor. No se imprimen credenciales.",file=sys.stderr)
        sys.exit(1)

if __name__=="__main__":
    main()
