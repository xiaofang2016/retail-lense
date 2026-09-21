from fastapi import Request

from core.security.ip import normalize_ip

__all__ = ["client_ip", "normalize_ip"]

# Streamlit sets this; Lambda Function URL CloudFront rewrites X-Forwarded-For.
CLIENT_IP_HEADER = "x-retaillen-client-ip"


def client_ip(request: Request) -> str:
    """Resolve the browser IP. Prefer the Streamlit-forwarded header."""
    custom = (request.headers.get(CLIENT_IP_HEADER) or "").split(",")[0].strip()
    if custom:
        return custom
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
        return ip or "unknown"
    return request.client.host if request.client else "unknown"
