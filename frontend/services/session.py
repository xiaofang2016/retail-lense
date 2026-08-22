"""JWT and current user in Streamlit session_state."""

from __future__ import annotations

from typing import Any

import streamlit as st

from services import api_client


def token() -> str | None:
    return st.session_state.get("access_token")


def current_user() -> dict[str, Any] | None:
    return st.session_state.get("user")


def signed_in() -> bool:
    return bool(token())


def save_login(access_token: str) -> dict[str, Any]:
    user = api_client.me(access_token)
    st.session_state["access_token"] = access_token
    st.session_state["user"] = user
    return user


def sign_out() -> None:
    st.session_state.pop("access_token", None)
    st.session_state.pop("user", None)
