"""SQLite monoinstancia: inbox, tokens e idempotencia cifrados con Fernet.

Las filas pendientes de envío no se reejecutan automáticamente tras un fallo:
no se puede prometer exactly-once si un proveedor aceptó un mensaje y se cortó la red.
La reconciliación es una decisión humana: `pending()` muestra qué quedó en duda y
`release()` libera la reserva únicamente cuando alguien confirma el resultado real.
"""
import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from .errors import IntegrationError

SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (name TEXT PRIMARY KEY, payload BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS requests (
    key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL,
    payload BLOB, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
    event_key TEXT NOT NULL, payload BLOB NOT NULL, created REAL NOT NULL,
    acked INTEGER NOT NULL DEFAULT 0, UNIQUE(source,event_key));
CREATE INDEX IF NOT EXISTS events_pending ON events(acked, id);
CREATE INDEX IF NOT EXISTS requests_status ON requests(status, created);
"""


class Store:
    def __init__(self, path: str, key: str):
        if not key:
            raise ValueError("STATE_KEY requerida; ejecute python scripts/bootstrap.py")
        self.cipher = Fernet(key.encode())
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(SCHEMA)
        if os.name != "nt":
            os.chmod(path, 0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        # WAL permite leer el inbox mientras una escritura reserva su clave de idempotencia.
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def encode(self, value):
        return self.cipher.encrypt(json.dumps(value, ensure_ascii=False).encode())

    def decode(self, value):
        return json.loads(self.cipher.decrypt(value))

    def token_get(self, name):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM tokens WHERE name=?", (name,)).fetchone()
        return self.decode(row["payload"]) if row else None

    def token_put(self, name, value):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO tokens VALUES (?,?)", (name, self.encode(value)))

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()

    def reserve(self, key, request):
        """Reserva la clave y guarda cifrado qué se intentó, para poder reconciliarlo luego."""
        fingerprint = self.digest(json.dumps(request, sort_keys=True))
        key = self.digest(key)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM requests WHERE key=?", (key,)).fetchone()
            if row:
                if row["fingerprint"] != fingerprint:
                    raise IntegrationError("IDEMPOTENCY_CONFLICT", 409)
                if row["status"] != "complete":
                    raise IntegrationError("OUTCOME_PENDING_OR_UNKNOWN_RECONCILE", 409)
                return self.decode(row["payload"])
            db.execute(
                "INSERT INTO requests VALUES (?,?,'pending',?,?)",
                (key, fingerprint, self.encode({"attempt": request}), time.time()),
            )
        return None

    def complete(self, key, value):
        key = self.digest(key)
        with self.connect() as db:
            db.execute("UPDATE requests SET status='complete',payload=? WHERE key=?", (self.encode(value), key))

    def pending(self, limit: int = 50) -> list[dict]:
        """Escrituras cuyo resultado real no se conoce. `id` es el identificador de reserva."""
        with self.connect() as db:
            rows = db.execute(
                "SELECT key, created, payload FROM requests WHERE status!='complete' ORDER BY created LIMIT ?",
                (limit,),
            ).fetchall()
        items = []
        for row in rows:
            attempt = {}
            try:
                attempt = (self.decode(row["payload"]) or {}).get("attempt", {}) if row["payload"] else {}
            except (InvalidToken, ValueError):
                attempt = {"decode_warning": "UNREADABLE_WITH_CURRENT_STATE_KEY"}
            items.append({
                "id": row["key"],
                "created": row["created"],
                "age_seconds": round(time.time() - row["created"], 2),
                "system": attempt.get("system"),
                "operation": attempt.get("operation"),
                "decode_warning": attempt.get("decode_warning"),
            })
        return items

    def release(self, reservation_id: str) -> bool:
        """Libera una reserva en duda para permitir un reintento deliberado.

        No contacta al proveedor ni deshace nada que este ya haya aceptado: quien libera
        afirma haber comprobado el resultado real por fuera del gateway.
        """
        with self.connect() as db:
            return db.execute(
                "DELETE FROM requests WHERE key=? AND status!='complete'", (reservation_id,)
            ).rowcount == 1

    def event_add(self, source, event_key, payload):
        with self.connect() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO events(source,event_key,payload,created) VALUES(?,?,?,?)",
                (source, event_key, self.encode(payload), time.time()),
            )
            return result.rowcount == 1

    def events(self, limit=50, after=0):
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE acked=0 AND id>? ORDER BY id LIMIT ?", (after, limit)
            ).fetchall()
        return [{"id": r["id"], "source": r["source"], "created": r["created"], "payload": self.decode(r["payload"])} for r in rows]

    def ack(self, event_id):
        with self.connect() as db:
            return db.execute("UPDATE events SET acked=1 WHERE id=?", (event_id,)).rowcount == 1

    def prune(self, days=30):
        """Expira solo inbox reconocido; no elimina claves de idempotencia sin reconciliación."""
        with self.connect() as db:
            return db.execute("DELETE FROM events WHERE acked=1 AND created<?", (time.time() - days * 86400,)).rowcount

    def prune_requests(self, days=90):
        """Expira solo reservas completadas; las pendientes sobreviven hasta reconciliarse."""
        with self.connect() as db:
            return db.execute(
                "DELETE FROM requests WHERE status='complete' AND created<?", (time.time() - days * 86400,)
            ).rowcount

    def stats(self) -> dict[str, int]:
        """Recuento operativo del estado local; nunca devuelve contenidos ni credenciales."""
        with self.connect() as db:
            def count(sql, args=()):
                return int(db.execute(sql, args).fetchone()[0])
            return {
                "events_pending": count("SELECT COUNT(*) FROM events WHERE acked=0"),
                "events_acked": count("SELECT COUNT(*) FROM events WHERE acked=1"),
                "requests_complete": count("SELECT COUNT(*) FROM requests WHERE status='complete'"),
                "requests_pending_reconciliation": count("SELECT COUNT(*) FROM requests WHERE status!='complete'"),
                "tokens_stored": count("SELECT COUNT(*) FROM tokens"),
            }
