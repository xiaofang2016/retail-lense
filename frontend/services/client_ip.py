"""Browser IP as seen by Streamlit (ALB X-Forwarded-For), not the frontend EC2 address."""

from __future__ import annotations

import ipaddress


def _header_value(headers: object, *names: str) -> str:
    if headers is None:
        return ""
    wanted = {name.lower() for name in names}
    getter = getattr(headers, "get", None)
    if callable(getter):
        for name in names:
            value = getter(name)
            if value:
                return str(value).strip()
    try:
        items = headers.items()  # type: ignore[attr-defined]
    except Exception:
        return ""
    for key, value in items:
        if str(key).lower() in wanted and value:
            return str(value).strip()
    return ""


def _hops(forwarded: str) -> list[str]:
    return [part.strip() for part in forwarded.split(",") if part.strip()]


def _valid_ip(raw: str) -> str | None:
    text = raw.split("%", 1)[0].strip().strip("[]")
    if not text:
        return None
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return None


def pick_client_ip(forwarded: str = "", real_ip: str = "", fallback: str = "") -> str:
    """ALB appends the connecting client at the end of X-Forwarded-For.

    Prefer the rightmost public address so a client-supplied spoofed hop is ignored.
    If every hop is private (local Compose), use the last hop.
    """
    candidates = [_valid_ip(hop) for hop in reversed(_hops(forwarded))]
    public = [ip for ip in candidates if ip and not ipaddress.ip_address(ip).is_private]
    if public:
        return public[0]
    private = [ip for ip in candidates if ip]
    if private:
        return private[0]
    for raw in (real_ip, fallback):
        ip = _valid_ip(raw)
        if ip:
            return ip
    return ""


def browser_ip() -> str:
    """Client IP from the current Streamlit request, or empty outside a session."""
    try:
        import streamlit as st

        headers = st.context.headers
    except Exception:
        return ""
    forwarded = _header_value(headers, "X-Forwarded-For", "x-forwarded-for")
    real_ip = _header_value(headers, "X-Real-IP", "x-real-ip")
    fallback = ""
    try:
        fallback = str(getattr(st.context, "ip", "") or "")
    except Exception:
        fallback = ""
    return pick_client_ip(forwarded, real_ip, fallback)


def browser_user_agent() -> str:
    try:
        import streamlit as st

        headers = st.context.headers
    except Exception:
        return ""
    return _header_value(headers, "User-Agent", "user-agent")
