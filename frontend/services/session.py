"""JWT and current user in Streamlit session_state."""

from __future__ import annotations

import os
import secrets
from typing import Any

import streamlit as st

from services import api_client, session_store

SESSION_COOKIE = "session_id"
COOKIE_PREFIX = "retaillen/"
COOKIE_MANAGER_STATE_KEY = "_retaillen_cookie_manager"


def _cookies():
    manager = st.session_state.get(COOKIE_MANAGER_STATE_KEY)
    if manager is not None:
        return manager

    password = os.getenv("SESSION_COOKIE_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("SESSION_COOKIE_PASSWORD is required when REDIS_URL is configured")
    from streamlit_cookies_manager import EncryptedCookieManager

    manager = EncryptedCookieManager(
        prefix=COOKIE_PREFIX,
        password=password,
    )
    if not manager.ready():
        # Do not cache an unready manager. The next Streamlit rerun must invoke
        # the component again to receive the browser cookies.
        st.stop()
    st.session_state[COOKIE_MANAGER_STATE_KEY] = manager
    return manager


def _restore() -> None:
    if st.session_state.get("access_token") or not session_store.enabled():
        return

    cookies = _cookies()
    session_id = cookies.get(SESSION_COOKIE)
    if not session_id:
        return

    saved = session_store.load(session_id)
    if saved is None:
        cookies.pop(SESSION_COOKIE, None)
        cookies.save()
        return

    st.session_state["access_token"] = saved["access_token"]
    st.session_state["user"] = saved.get("user")


def _session_ttl(remember_me: bool) -> int:
    if remember_me:
        return max(60, int(os.getenv("REMEMBER_ME_DAYS", "14")) * 86400)
    return max(60, int(os.getenv("TOKEN_TIME", "48")) * 3600)


def token() -> str | None:
    _restore()
    return st.session_state.get("access_token")


def current_user() -> dict[str, Any] | None:
    _restore()
    return st.session_state.get("user")


def signed_in() -> bool:
    return bool(token())


def save_login(access_token: str, remember_me: bool = False) -> dict[str, Any]:
    user = api_client.me(access_token)
    if session_store.enabled():
        session_id = secrets.token_urlsafe(32)
        session_store.save(
            session_id,
            access_token,
            user,
            ttl_seconds=_session_ttl(remember_me),
        )
        cookies = _cookies()
        cookies[SESSION_COOKIE] = session_id
        cookies.save()
    st.session_state["access_token"] = access_token
    st.session_state["user"] = user
    return user


def sign_out() -> None:
    try:
        if session_store.enabled():
            cookies = _cookies()
            session_id = cookies.get(SESSION_COOKIE)
            if session_id:
                session_store.delete(session_id)
            cookies.pop(SESSION_COOKIE, None)
            cookies.save()
    finally:
        st.session_state.pop("access_token", None)
        st.session_state.pop("user", None)
