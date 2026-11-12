"""Preparar carpetas y claves locales; no reemplazar claves existentes ni rotar STATE_KEY."""
import os
import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

root = Path(__file__).resolve().parents[1]
path = root / ".env"
text = path.read_text(encoding="utf-8") if path.exists() else (root / ".env.example").read_text(encoding="utf-8")
existing = dict(re.findall(r"^([A-Z_]+)=(.*)$", text, flags=re.MULTILINE))
for label, factory in {
    "GATEWAY_API_KEY": lambda: secrets.token_urlsafe(32),
    "APPROVAL_API_KEY": lambda: secrets.token_urlsafe(32),
    "STATE_KEY": lambda: Fernet.generate_key().decode(),
}.items():
    if existing.get(label, "").strip().strip('"').strip("'"):
        continue
    if label == "STATE_KEY" and any(p.suffix in {".db", ".sqlite", ".sqlite3"} for p in (root / "data").glob("*")):
        raise SystemExit("Existe una base de datos sin STATE_KEY: restaure su clave. No se genera una clave incompatible.")
    line = f"{label}={factory()}"
    text = re.sub(rf"^{label}=.*$", line, text, flags=re.MULTILINE) if label in existing else text.rstrip() + "\n" + line + "\n"
if "ALLOW_WRITES" not in existing:
    text += "\nALLOW_WRITES=false\n"
if os.name != "nt":
    for label, value in [("LOCAL_UID", os.getuid()), ("LOCAL_GID", os.getgid())]:
        if label not in existing:
            text += f"{label}={value}\n"
path.write_text(text, encoding="utf-8")
if os.name != "nt":
    os.chmod(path, 0o600)
for directory in ["data", "secrets"]:
    (root / directory).mkdir(exist_ok=True)
print("Configuración local preparada. Las claves existentes se conservaron; revise ALLOW_WRITES antes de operar.")
