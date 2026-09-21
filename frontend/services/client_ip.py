"""Browser IP as seen by Streamlit (ALB X-Forwarded-For), not the frontend EC2 address."""

from __future__ import annotations

import ipaddress

# Function URLs sit behind CloudFront, which rewrites X-Forwarded-For to the
# caller (the frontend public IP, e.g. 15.158.x). FastAPI/Lambda read this instead.
CLIENT_IP_HEADER = "x-retaillen-client-ip"


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


def _is_public(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (addr.is_private or addr.is_loopback or addr.is_link_local)


def pick_client_ip(
    forwarded: str = "",
    real_ip: str = "",
    fallback: str = "",
    viewer_address: str = "",
) -> str:
    """Original client is the leftmost public hop (browser → CloudFront → ALB).

    The rightmost hop is often CloudFront (15.158.x), not the browser.
    """
    viewer = viewer_address.split("%", 1)[0].strip()
    if viewer.count(":") == 1 and "." in viewer:
        viewer = viewer.rsplit(":", 1)[0]
    ip = _valid_ip(viewer)
    if ip and _is_public(ip):
        return ip

    hops = [_valid_ip(hop) for hop in _hops(forwarded)]
    public = [ip for ip in hops if ip and _is_public(ip)]
    if public:
        return public[0]
    private = [ip for ip in hops if ip]
    if private:
        return private[0]
    for raw in (real_ip, fallback):
        parsed = _valid_ip(raw)
        if parsed:
            return parsed
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
    viewer = _header_value(headers, "CloudFront-Viewer-Address", "cloudfront-viewer-address")
    fallback = ""
    try:
        fallback = str(getattr(st.context, "ip", "") or "")
    except Exception:
        fallback = ""
    return pick_client_ip(forwarded, real_ip, fallback, viewer)


def browser_user_agent() -> str:
    try:
        import streamlit as st

        headers = st.context.headers
    except Exception:
        return ""
    return _header_value(headers, "User-Agent", "user-agent")
