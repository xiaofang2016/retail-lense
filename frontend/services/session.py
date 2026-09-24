"""JWT and current user in Streamlit session_state."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import time
from typing import Any

import streamlit as st

from services import api_client, session_store

logger = logging.getLogger("retaillen.frontend.session")

SESSION_COOKIE = "session_id"
BROWSER_COOKIE_NAME = "retaillen_session_id"
_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def cookies_enabled() -> bool:
    return session_store.enabled()


def prepare(*, remount: bool = False) -> None:
    """Restore Redis sessions and persist the session cookie if needed.

    remount is accepted for call-site compatibility. Browser cookies are read
    from the HTTP request (st.context.cookies), so there is no iframe to remount.
    """
    del remount
    if not cookies_enabled():
        return

    _restore()

    # main.py reads access_token before pg.run(); refresh nav after a cookie restore.
    if st.session_state.get("access_token") and not st.session_state.get("_retaillen_nav_synced"):
        st.session_state["_retaillen_nav_synced"] = True
        st.rerun()

    # Write after any rerun above so switch_page/rerun cannot abort the iframe.
    _flush_pending_session_cookie()


def _cookie_password() -> str:
    password = os.getenv("SESSION_COOKIE_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("SESSION_COOKIE_PASSWORD is required when REDIS_URL is configured")
    return password


def _sign_session_id(session_id: str) -> str:
    digest = hmac.new(
        _cookie_password().encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{session_id}.{digest}"


def _unsign_session_id(raw: str) -> str | None:
    if not raw or "." not in raw:
        return None
    session_id, digest = raw.rsplit(".", 1)
    if not _SESSION_ID_RE.fullmatch(session_id) or not digest:
        return None
    expected = hmac.new(
        _cookie_password().encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    return session_id


def _browser_cookies() -> dict[str, str]:
    try:
        cookies = st.context.cookies
    except Exception:
        return {}
    if cookies is None:
        return {}
    try:
        if hasattr(cookies, "to_dict"):
            data = cookies.to_dict()
        else:
            data = dict(cookies)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value is not None}


def _read_session_cookie() -> str | None:
    try:
        return _unsign_session_id(_browser_cookies().get(BROWSER_COOKIE_NAME, ""))
    except RuntimeError:
        return None


def _cookie_secure() -> bool:
    url = str(getattr(st.context, "url", "") or "")
    if url.startswith("https://"):
        return True
    try:
        headers = st.context.headers
    except Exception:
        return False
    proto = ""
    if headers is not None:
        proto = str(headers.get("X-Forwarded-Proto") or headers.get("x-forwarded-proto") or "")
    return proto.split(",", 1)[0].strip().lower() == "https"


def _write_browser_cookie(session_id: str | None, max_age: int = 0) -> None:
    if session_id is None:
        assignment = f"{BROWSER_COOKIE_NAME}=; path=/; max-age=0"
    else:
        if not _SESSION_ID_RE.fullmatch(session_id):
            logger.warning("refusing to write invalid session id")
            return
        flags = f"path=/; max-age={int(max_age)}; SameSite=Lax"
        if _cookie_secure():
            flags += "; Secure"
        assignment = f"{BROWSER_COOKIE_NAME}={_sign_session_id(session_id)}; {flags}"
    if any(char in assignment for char in '"<>\\\n\r'):
        logger.warning("refusing to write unsafe cookie assignment")
        return
    st.iframe(
        f"<script>document.cookie = {assignment!r};</script>",
        height=1,
    )


def _active_session_id() -> str | None:
    pending = st.session_state.get("_pending_session_id")
    if pending:
        return pending
    stored = st.session_state.get("_session_id")
    if stored:
        return stored
    return _read_session_cookie()


def _queue_session_cookie(session_id: str) -> None:
    st.session_state["_session_id"] = session_id
    st.session_state["_pending_session_id"] = session_id
    st.session_state["_pending_session_ttl"] = _session_ttl(bool(st.session_state.get("remember_me")))
    st.session_state.pop("_pending_session_delete", None)
    # Do not write the cookie here. components.html never runs if this script
    # then switch_page/rerun. prepare() writes it on the next run instead.


def _queue_session_cookie_delete() -> None:
    st.session_state["_pending_session_delete"] = True
    st.session_state.pop("_pending_session_id", None)
    st.session_state.pop("_pending_session_ttl", None)
    st.session_state.pop("_session_id", None)


def _flush_pending_session_cookie() -> None:
    if st.session_state.get("_pending_session_delete"):
        _write_browser_cookie(None)
        st.session_state.pop("_pending_session_delete", None)
        return
    pending_session_id = st.session_state.get("_pending_session_id")
    if not pending_session_id:
        return
    max_age = int(st.session_state.get("_pending_session_ttl") or _session_ttl(False))
    _write_browser_cookie(pending_session_id, max_age=max_age)
    st.session_state.pop("_pending_session_id", None)
    st.session_state.pop("_pending_session_ttl", None)


def _restore() -> None:
    if not cookies_enabled():
        return

    session_id = _read_session_cookie()
    if not session_id:
        return

    saved = session_store.load(session_id)
    if saved is None:
        if st.session_state.get("access_token"):
            return
        _queue_session_cookie_delete()
        return

    st.session_state["_session_id"] = session_id
    if not st.session_state.get("access_token"):
        st.session_state["access_token"] = saved["access_token"]
        st.session_state["refresh_token"] = saved.get("refresh_token")
        st.session_state["remember_me"] = bool(saved.get("remember_me"))
        if saved.get("user") is not None:
            st.session_state["user"] = saved["user"]
    _refresh_user_from_api()


def _decode_token_payload(token: str) -> dict[str, Any]:
    if not token or token.count(".") != 2:
        return {}
    _header, payload, _signature = token.split(".", 2)
    if not payload:
        return {}
    try:
        padded = payload + "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _token_has_expired(token: str | None) -> bool:
    if not token:
        return True
    payload = _decode_token_payload(token)
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return True
    try:
        return float(exp) <= time.time()
    except (TypeError, ValueError):
        return True


def _session_ttl(remember_me: bool) -> int:
    if remember_me:
        return max(60, int(os.getenv("REMEMBER_ME_DAYS", "14")) * 86400)
    return max(60, int(os.getenv("TOKEN_TIME", "48")) * 3600)


_USER_REFRESH_SECONDS = 30


def _refresh_user_from_api() -> None:
    """Reload is_admin and other public fields from FastAPI.

    Frontend EC2 has no AWS role, so ops promote users in DynamoDB on the
    backend. Redis may still hold a stale user until we refetch /users/me.
    """
    access_token = st.session_state.get("access_token")
    if not access_token or _token_has_expired(access_token):
        return
    now = time.time()
    last = float(st.session_state.get("_user_refreshed_at") or 0)
    if last and now - last < _USER_REFRESH_SECONDS:
        return
    try:
        user = api_client.me(access_token)
    except Exception:
        return
    if not isinstance(user, dict):
        return
    st.session_state["_user_refreshed_at"] = now
    previous = st.session_state.get("user")
    st.session_state["user"] = user
    if previous == user or not cookies_enabled():
        return
    session_id = _active_session_id()
    if not session_id:
        return
    saved = session_store.load(session_id) or {}
    session_store.save(
        session_id,
        saved.get("access_token") or access_token,
        user,
        ttl_seconds=_session_ttl(bool(saved.get("remember_me") or st.session_state.get("remember_me"))),
        refresh_token=saved.get("refresh_token") or st.session_state.get("refresh_token"),
        remember_me=bool(saved.get("remember_me") or st.session_state.get("remember_me")),
    )


def token() -> str | None:
    _restore()
    access_token = st.session_state.get("access_token")
    refresh_token_value = st.session_state.get("refresh_token")
    if access_token and _token_has_expired(access_token):
        if not refresh_token_value:
            if cookies_enabled():
                session_id = _active_session_id()
                if session_id:
                    saved = session_store.load(session_id)
                    if saved:
                        refresh_token_value = saved.get("refresh_token")
            if not refresh_token_value:
                sign_out()
                return None

        try:
            data = api_client.refresh_access_token(refresh_token_value)
        except Exception:
            sign_out()
            return None

        new_access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token") or refresh_token_value
        if not new_access_token:
            sign_out()
            return None

        st.session_state["access_token"] = new_access_token
        st.session_state["refresh_token"] = new_refresh_token

        if cookies_enabled():
            session_id = _active_session_id()
            if session_id:
                saved = session_store.load(session_id) or {}
                session_store.save(
                    session_id,
                    new_access_token,
                    saved.get("user") or st.session_state.get("user") or {},
                    ttl_seconds=_session_ttl(bool(saved.get("remember_me") or st.session_state.get("remember_me"))),
                    refresh_token=new_refresh_token,
                    remember_me=bool(saved.get("remember_me") or st.session_state.get("remember_me")),
                )

        return new_access_token
    return access_token


def current_user() -> dict[str, Any] | None:
    _restore()
    _refresh_user_from_api()
    return st.session_state.get("user")


def signed_in() -> bool:
    return bool(token())


def save_login(
    access_token: str,
    remember_me: bool = False,
    refresh_token_value: str | None = None,
    refresh_token: str | None = None,
) -> dict[str, Any]:
    refresh_token_value = refresh_token_value if refresh_token_value is not None else refresh_token
    user = api_client.me(access_token)
    st.session_state["access_token"] = access_token
    st.session_state["refresh_token"] = refresh_token_value
    st.session_state["remember_me"] = remember_me
    st.session_state["user"] = user

    if cookies_enabled():
        session_id = secrets.token_urlsafe(32)
        if not session_store.save(
            session_id,
            access_token,
            user,
            ttl_seconds=_session_ttl(remember_me),
            refresh_token=refresh_token_value,
            remember_me=remember_me,
        ):
            return user
        _queue_session_cookie(session_id)
        logger.info("save_login: queued signed session cookie for the next page run")
    return user


def sign_out() -> None:
    try:
        if cookies_enabled():
            session_id = _active_session_id()
            if session_id:
                session_store.delete(session_id)
            _queue_session_cookie_delete()
    finally:
        st.session_state.pop("access_token", None)
        st.session_state.pop("refresh_token", None)
        st.session_state.pop("remember_me", None)
        st.session_state.pop("user", None)
        st.session_state.pop("_pending_login", None)
        st.session_state.pop("_pending_session_id", None)
        st.session_state.pop("_pending_session_ttl", None)
        st.session_state.pop("_session_id", None)
        st.session_state.pop("_retaillen_nav_synced", None)
        st.session_state.pop("_user_refreshed_at", None)
