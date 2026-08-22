from functools import lru_cache
from typing import Protocol

import bcrypt

from core.settings import get_settings


class Hasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed: str) -> bool: ...


class FakeHasher:
    def hash(self, password: str) -> str:
        return password

    def verify(self, password: str, hashed: str) -> bool:
        return password == hashed


class BcryptHasher:
    def _get_password_bytes(self, password: str) -> bytes:
        return password.encode("utf-8")[:72]

    def hash(self, password: str) -> str:
        password_bytes = self._get_password_bytes(password)
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, password: str, hashed: str) -> bool:
        password_bytes = self._get_password_bytes(password)
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)


# Constant-time dummy used when the username is unknown.
FAKE_PASSWORD_HASH = "$2b$12$JdHtJOlkPFwyxdjdygEzPOtYmdQF5/R5tHxw5Tq8pxjubyLqdIX5i"


@lru_cache(maxsize=1)
def get_hasher() -> Hasher:
    if get_settings().app_env == "test":
        return FakeHasher()
    return BcryptHasher()
