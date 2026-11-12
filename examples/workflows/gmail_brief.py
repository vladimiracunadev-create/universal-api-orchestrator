"""Buscar IDs y consultar los cuerpos seleccionados; preparar respuesta, NUNCA enviar."""
from __future__ import annotations
import argparse
import json
import os
import httpx
from dotenv import load_dotenv


def call(client: httpx.Client, path: str, body: dict) -> dict:
    response = client.post(path, json=body)
    response.raise_for_status()
    result = response.json()
    if result.get("ok") is False:
        raise ValueError("La operación de origen falló; revise el sobre de error en el gateway.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="is:unread")
    parser.add_argument("--limit", type=int, default=3, choices=range(1, 11))
    args = parser.parse_args()
    load_dotenv(override=False)
    key = os.environ.get("GATEWAY_API_KEY")
    if not key:
        raise SystemExit("Falta GATEWAY_API_KEY")
    with httpx.Client(base_url=os.getenv("GATEWAY_URL", "http://127.0.0.1:8080"), headers={"X-API-Key": key}, timeout=90, trust_env=False) as client:
        listing = call(client, "/v1/execute", {"system": "gmail", "operation": "list_messages", "params": {"q": args.query, "maxResults": args.limit}})
        messages = listing.get("data", {}).get("messages", [])
        if not messages:
            print("No se encontraron mensajes para esa consulta. No se preparó ningún envío.")
            return
        answer = call(client, "/v1/ask", {
            "question": "Identifica solicitudes y pendientes en los mensajes. Cita sus alias; no inventes acciones realizadas. No envíes nada.",
            "requests": [{"alias": f"correo_{i+1}", "system": "gmail", "operation": "get_message", "params": {"id": item["id"], "format": "full"}} for i, item in enumerate(messages[:args.limit])],
        })
        print(json.dumps(answer, ensure_ascii=False, indent=2))
        if answer.get("errors"):
            raise SystemExit(2)

if __name__ == "__main__":
    try:
        main()
    except (httpx.HTTPError, ValueError, KeyError):
        raise SystemExit("Falló la consulta. Revise conexión, credenciales y permisos; no se ha enviado ningún mensaje.")
