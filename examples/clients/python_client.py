"""Cliente de SOLO LECTURA. Ejecutar desde la raíz con la instalación activa."""
from __future__ import annotations
import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=False)
def main() -> None:
    key = os.environ.get("GATEWAY_API_KEY", "")
    if not key:
        raise SystemExit("Falta GATEWAY_API_KEY. Ejecute scripts/bootstrap.py.")
    with httpx.Client(base_url=os.getenv("GATEWAY_URL", "http://127.0.0.1:8080"), timeout=60, trust_env=False) as client:
        response = client.post("/v1/execute", headers={"X-API-Key": key}, json={
            "system": "gmail", "operation": "list_messages",
            "params": {"q": "is:unread", "maxResults": 5},
        })
        response.raise_for_status()
        result = response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(2)
if __name__ == "__main__":
    main()
