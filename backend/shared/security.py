"""Password hashing helpers used by auth. Implementation lives in core.security.hasher."""

from core.security.hasher import get_hasher


def hash_password(plain: str) -> str:
    return get_hasher().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return get_hasher().verify(plain, hashed)


def password_is_strong(plain: str) -> bool:
    return len(plain) >= 8
