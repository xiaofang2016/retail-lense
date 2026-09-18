"""Optional Redis store for shared Streamlit login sessions.

If REDIS_URL is empty or Redis is unreachable, callers should keep the JWT in
Streamlit session_state only. Login must not require Redis.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Any

import redis
from redis.exceptions import RedisError

logger = logging.getLogger("retaillen.frontend.session_store")

SESSION_KEY_PREFIX = "retaillen:session:"
_available: bool | None = None


def enabled() -> bool:
    global _available
    if not os.getenv("REDIS_URL", "").strip():
        return False
    if _available is not None:
        return _available
    try:
        _client().ping()
        _available = True
    except Exception as exc:
        logger.warning(
            "Redis is not reachable; login will use Streamlit session_state only: %s",
            exc,
        )
        _available = False
        _client.cache_clear()
    return _available


def _mark_unavailable(exc: BaseException) -> None:
    global _available
    if _available is not False:
        logger.warning("Redis failed; falling back to Streamlit session_state: %s", exc)
    _available = False
    _client.cache_clear()


@lru_cache(maxsize=1)
def _client() -> redis.Redis:
    url = os.getenv("REDIS_URL", "").strip()
    if not url:
        raise RuntimeError("REDIS_URL is not configured")
    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )


def _key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def save(
    session_id: str,
    access_token: str,
    user: dict[str, Any],
    ttl_seconds: int,
    refresh_token: str | None = None,
    remember_me: bool = False,
) -> bool:
    if not enabled():
        return False
    payload = json.dumps(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
            "remember_me": remember_me,
        },
        separators=(",", ":"),
    )
    try:
        _client().set(_key(session_id), payload, ex=ttl_seconds)
        return True
    except (RedisError, OSError) as exc:
        _mark_unavailable(exc)
        return False


def load(session_id: str) -> dict[str, Any] | None:
    if not enabled():
        return None
    try:
        payload = _client().get(_key(session_id))
    except (RedisError, OSError) as exc:
        _mark_unavailable(exc)
        return None
    if not payload:
        return None
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        delete(session_id)
        return None
    if not isinstance(value, dict) or not isinstance(value.get("access_token"), str):
        delete(session_id)
        return None
    return value


def delete(session_id: str) -> None:
    if not enabled():
        return
    try:
        _client().delete(_key(session_id))
    except (RedisError, OSError) as exc:
        _mark_unavailable(exc)
