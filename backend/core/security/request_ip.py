from fastapi import Request

from core.security.ip import normalize_ip

__all__ = ["client_ip", "normalize_ip"]


def client_ip(request: Request) -> str:
    """Resolve the caller IP. Prefer the first X-Forwarded-For hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        return ip or "unknown"
    return request.client.host if request.client else "unknown"
