"""Defensa de salida. Debe complementarse con firewall/proxy de egreso contra DNS rebinding."""
import ipaddress
import socket
from urllib.parse import urlparse

from .config import settings
from .errors import IntegrationError

FORBIDDEN_HEADERS = {"authorization", "host", "cookie", "proxy-authorization", "x-api-key"}

def assert_safe_endpoint(url: str, allowed_hosts: list[str] | None = None) -> None:
    parsed = urlparse(url if "://" in url else f"tcp://{url}")
    host = parsed.hostname
    if not host or parsed.username or parsed.password or parsed.fragment:
        raise IntegrationError("UNSAFE_ENDPOINT")
    if parsed.scheme not in {"https", "http", "tcp"}:
        raise IntegrationError("UNSAFE_SCHEME")
    if not allowed_hosts or host.lower() not in {h.lower() for h in allowed_hosts}:
        raise IntegrationError("HOST_NOT_ALLOWED")
    if parsed.scheme == "http" and not settings.allow_private_networks:
        raise IntegrationError("TLS_REQUIRED")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port)}
    except socket.gaierror as exc:
        raise IntegrationError("DNS_UNRESOLVED") from exc
    if not settings.allow_private_networks:
        if any(not ipaddress.ip_address(addr).is_global for addr in addresses):
            raise IntegrationError("PRIVATE_NETWORK_BLOCKED")

def safe_caller_headers(headers: dict[str, str], allowed: list[str]) -> dict[str, str]:
    allowed = {h.lower() for h in allowed}
    if any(k.lower() in FORBIDDEN_HEADERS or k.lower() not in allowed for k in headers):
        raise IntegrationError("CALLER_HEADER_NOT_ALLOWED", 403)
    return headers
