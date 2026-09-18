"""Shared Streamlit login sessions stored in Redis."""

from __future__ import annotations

from asyncio.log import logger
import json
import os
from functools import lru_cache
from typing import Any

import redis

SESSION_KEY_PREFIX = "retaillen:session:"


def enabled() -> bool:
    return bool(os.getenv("REDIS_URL", "").strip())


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
) -> None:
    payload = json.dumps(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
            "remember_me": remember_me,
        },
        separators=(",", ":"),
    )
    _client().set(_key(session_id), payload, ex=ttl_seconds)


def load(session_id: str) -> dict[str, Any] | None:
    payload = _client().get(_key(session_id))
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
    _client().delete(_key(session_id))
