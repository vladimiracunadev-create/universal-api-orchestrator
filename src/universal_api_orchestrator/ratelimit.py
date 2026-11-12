"""Control de carga local en memoria.

Protege la instancia de ráfagas y de bucles de cliente mal configurados. No sustituye un
WAF, un proxy inverso ni un límite compartido entre réplicas: el contador vive en este
proceso y se reinicia al reiniciarlo.
"""
import hashlib
import time


class RateLimiter:
    """Token bucket por identidad de llamada. `per_minute=0` desactiva el control."""

    def __init__(self, per_minute: int, burst: int, max_identities: int = 4096):
        self.rate = max(0, per_minute) / 60.0
        self.burst = max(1, burst)
        self.max_identities = max_identities
        self.buckets: dict[str, tuple[float, float]] = {}

    @staticmethod
    def identity(api_key: str, client_host: str) -> str:
        """No se almacena la clave: solo un resumen estable para contar peticiones."""
        material = api_key or f"ip:{client_host}"
        return hashlib.sha256(material.encode()).hexdigest()[:32]

    def check(self, identity: str, now: float | None = None) -> tuple[bool, int, float]:
        """Devuelve (permitido, tokens restantes, segundos sugeridos de espera)."""
        if self.rate <= 0:
            return True, self.burst, 0.0
        now = now if now is not None else time.monotonic()
        tokens, updated = self.buckets.get(identity, (float(self.burst), now))
        tokens = min(self.burst, tokens + (now - updated) * self.rate)
        if tokens < 1:
            self.buckets[identity] = (tokens, now)
            return False, 0, round((1 - tokens) / self.rate, 3)
        tokens -= 1
        if identity not in self.buckets and len(self.buckets) >= self.max_identities:
            self._evict(now)
        self.buckets[identity] = (tokens, now)
        return True, int(tokens), 0.0

    def _evict(self, now: float) -> None:
        """Descarta buckets ya recargados; evita crecimiento ilimitado del diccionario."""
        full = [key for key, (tokens, updated) in self.buckets.items()
                if min(self.burst, tokens + (now - updated) * self.rate) >= self.burst]
        for key in full or list(self.buckets)[: self.max_identities // 4]:
            self.buckets.pop(key, None)
