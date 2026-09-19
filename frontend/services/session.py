"""JWT and current user in Streamlit session_state."""

from __future__ import annotations

import base64
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
_COOKIE_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
COOKIE_QUEUE_STATE_KEY = "CookieManager.queue"


def _validate_cookie_prefix(prefix: str) -> str:
    if not _COOKIE_NAME_RE.fullmatch(prefix):
        raise RuntimeError(
            f"Invalid cookie prefix {prefix!r}; browser cookie names cannot include '/', spaces, or other non-token characters."
        )
    return prefix


COOKIE_PREFIX = _validate_cookie_prefix("retaillen_")
COOKIE_MANAGER_STATE_KEY = "_retaillen_cookie_manager"
COOKIE_COMPONENT_KEY = "CookieManager.sync_cookies"


def cookies_enabled() -> bool:
    return session_store.enabled()


def prepare(*, remount: bool = False) -> None:
    """Mount the cookie component once per script run and restore Redis sessions.

    EncryptedCookieManager uses a fixed Streamlit key, so it must be constructed
    only once per run. Call with remount=True from main.py so a new instance is
    created on each rerun; reusing a cached manager across reruns leaves it
    stuck as not-ready.
    """
    if not cookies_enabled():
        return

    if remount and not _cookie_manager_mounted_this_run():
        st.session_state.pop(COOKIE_MANAGER_STATE_KEY, None)

    cookies = _cookies()
    if not cookies.ready():
        # Do not st.rerun() here: that aborts the cookie component before it
        # can report document.cookie. The component triggers a rerun itself.
        st.stop()

    _flush_pending_session_cookie()
    _flush_pending_login()

    # main.py reads access_token before pg.run(); refresh nav after a cookie restore.
    if st.session_state.get("access_token") and not st.session_state.get("_retaillen_nav_synced"):
        st.session_state["_retaillen_nav_synced"] = True
        st.rerun()


def _script_run_ctx():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        try:
            from streamlit.runtime.scriptrunner_utils.script_run_context import (
                get_script_run_ctx,
            )
        except ImportError:
            return None
    return get_script_run_ctx()


def _widget_user_keys_this_run():
    ctx = _script_run_ctx()
    if ctx is None:
        return None
    keys = getattr(ctx, "widget_user_keys_this_run", None)
    if keys is not None:
        return keys
    shared = getattr(ctx, "shared", None)
    if shared is None:
        return None
    return getattr(shared, "widget_user_keys_this_run", None)


def _cookie_manager_mounted_this_run() -> bool:
    user_keys = _widget_user_keys_this_run()
    if user_keys is None:
        return False
    try:
        return COOKIE_COMPONENT_KEY in user_keys
    except TypeError:
        return False


def _cached_cookie_manager():
    cached = st.session_state.get(COOKIE_MANAGER_STATE_KEY)
    if isinstance(cached, tuple) and len(cached) == 2:
        return cached[1]
    return cached


def _new_cookie_manager():
    password = os.getenv("SESSION_COOKIE_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("SESSION_COOKIE_PASSWORD is required when REDIS_URL is configured")
    from streamlit_cookies_manager import EncryptedCookieManager

    return EncryptedCookieManager(
        prefix=COOKIE_PREFIX,
        password=password,
    )


def _cookies():
    cached = _cached_cookie_manager()
    if cached is not None:
        if _cookie_manager_mounted_this_run() or _widget_user_keys_this_run() is None:
            return cached

    manager = _new_cookie_manager()
    st.session_state[COOKIE_MANAGER_STATE_KEY] = manager
    return manager


def _cookie_session_id(cookies) -> str | None:
    try:
        session_id = cookies.get(SESSION_COOKIE)
    except Exception:
        return None
    return session_id or None


def _queue_session_cookie(session_id: str) -> None:
    cookies = _cookies()
    cookies[SESSION_COOKIE] = session_id
    st.session_state["_pending_session_id"] = session_id
    # Do not call cookies.save() here. save() uses a second component that
    # never runs if this script then switch_page/rerun. CookieManager.__init__
    # on the next run sends CookieManager.queue to the main component, which
    # writes document.cookie.


def _queue_session_cookie_delete() -> None:
    """Queue a delete. CookieManager.__delitem__ ignores prefixed cookie names."""
    queue = st.session_state.setdefault(COOKIE_QUEUE_STATE_KEY, {})
    if isinstance(queue, dict):
        queue[SESSION_COOKIE] = {"value": None, "path": "/"}
    st.session_state.pop("_pending_session_id", None)


def _flush_pending_session_cookie() -> None:
    pending_session_id = st.session_state.get("_pending_session_id")
    if not pending_session_id:
        return
    cookies = _cookies()
    if not cookies.ready():
        return
    cookies[SESSION_COOKIE] = pending_session_id
    if _cookie_session_id(cookies) == pending_session_id:
        st.session_state.pop("_pending_session_id", None)


def _restore() -> None:
    if cookies_enabled():
        _flush_pending_session_cookie()
    if not cookies_enabled():
        return

    cookies = _cookies()
    if not cookies.ready():
        return

    session_id = _cookie_session_id(cookies)
    if not session_id:
        return

    saved = session_store.load(session_id)
    if saved is None:
        if st.session_state.get("access_token"):
            return
        _queue_session_cookie_delete()
        return

    if not st.session_state.get("access_token"):
        st.session_state["access_token"] = saved["access_token"]
        st.session_state["refresh_token"] = saved.get("refresh_token")
        st.session_state["remember_me"] = bool(saved.get("remember_me"))
    if saved.get("user") is not None:
        st.session_state["user"] = saved["user"]


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


def token() -> str | None:
    _restore()
    access_token = st.session_state.get("access_token")
    refresh_token_value = st.session_state.get("refresh_token")
    if access_token and _token_has_expired(access_token):
        if not refresh_token_value:
            if cookies_enabled():
                cookies = _cookies()
                if cookies.ready():
                    session_id = _cookie_session_id(cookies)
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
            cookies = _cookies()
            if cookies.ready():
                session_id = _cookie_session_id(cookies)
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
        cookies = _cookies()
        if not cookies.ready():
            st.session_state["_pending_login"] = {
                "access_token": access_token,
                "remember_me": remember_me,
                "refresh_token": refresh_token_value,
            }
            logger.info("save_login: cookies not ready, queued pending login for the next rerun")
            return user

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
        logger.info("save_login: queued encrypted session cookie for the next cookie-manager run")
    return user


def _flush_pending_login() -> None:
    pending = st.session_state.get("_pending_login")
    if not isinstance(pending, dict) or not pending.get("access_token"):
        return
    st.session_state.pop("_pending_login", None)
    save_login(
        pending["access_token"],
        remember_me=bool(pending.get("remember_me")),
        refresh_token_value=pending.get("refresh_token"),
    )


def sign_out() -> None:
    try:
        if cookies_enabled():
            cookies = _cookies()
            if cookies.ready():
                session_id = _cookie_session_id(cookies)
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
        st.session_state.pop("_retaillen_nav_synced", None)
