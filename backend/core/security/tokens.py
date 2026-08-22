import secrets
from datetime import UTC, datetime, timedelta

import jwt

from core.settings import get_settings

ALGORITHM = "HS256"


def create_access_token(user_id: str, remember_me: bool = False) -> str:
    settings = get_settings()
    duration = timedelta(hours=settings.token_time_hours)
    if remember_me:
        duration = max(timedelta(days=settings.remember_me_days), duration)
    expire = datetime.now(UTC) + duration
    payload = {"sub": user_id, "exp": expire, "iss": settings.issuer}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], issuer=settings.issuer)


def url_safe_token() -> str:
    """Cryptographic token with no embedded data. Used for password reset links."""
    return secrets.token_urlsafe(24)
