import ipaddress

from fastapi import Request


def client_ip(request: Request) -> str:
    """Resolve the caller IP. Prefer the first X-Forwarded-For hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        return ip or "unknown"
    return request.client.host if request.client else "unknown"


def normalize_ip(raw: str) -> str:
    """Canonical IPv4/IPv6 string. Raises ValueError if not an address."""
    text = (raw or "").strip()
    if not text or text.lower() == "unknown":
        raise ValueError("invalid IP")
    return str(ipaddress.ip_address(text.split("%")[0]))
