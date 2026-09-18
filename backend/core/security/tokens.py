import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from core.settings import get_settings

ALGORITHM = "HS256"


def _token_payload(user_id: str, *, ttl: timedelta, token_type: str) -> dict:
    issued_at = datetime.now(UTC)
    expire = issued_at + ttl
    return {
        "sub": user_id,
        "exp": expire,
        "iat": issued_at,
        "jti": str(uuid4()),
        "iss": get_settings().issuer,
        "type": token_type,
    }


def create_access_token(user_id: str, remember_me: bool = False) -> str:
    settings = get_settings()
    duration = timedelta(hours=settings.token_time_hours)
    if remember_me:
        duration = max(timedelta(days=settings.remember_me_days), duration)
    payload = _token_payload(user_id, ttl=duration, token_type="access")
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, remember_me: bool = False) -> str:
    settings = get_settings()
    duration = timedelta(days=7)
    if remember_me:
        duration = max(timedelta(days=settings.remember_me_days), duration)
    payload = _token_payload(user_id, ttl=duration, token_type="refresh")
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], issuer=settings.issuer)
    if payload.get("type") not in {None, "access"}:
        raise jwt.InvalidTokenError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], issuer=settings.issuer)
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Invalid refresh token")
    return payload


def url_safe_token() -> str:
    """Cryptographic token with no embedded data. Used for password reset links."""
    return secrets.token_urlsafe(24)
