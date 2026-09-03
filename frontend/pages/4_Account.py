"""Current user, login history, and per-account blocked IPs."""

import streamlit as st

from components.style import setup
from services import api_client, session
from services.api_client import ApiError

setup("Account")

st.title("Account")

if not session.signed_in():
    st.write("Sign in to see this page.")
    st.stop()

token = session.token() or ""
user = session.current_user() or {}
st.write(user.get("full_name") or "")
st.caption(f"{user.get('username', '')} · {user.get('email', '')}")

if st.button("Sign out"):
    session.sign_out()
    # Let the cookie component finish deleting the browser session cookie.
    st.success("Signed out.")
    st.stop()

st.divider()
st.subheader("Blocked IPs")
st.caption("Blocked addresses cannot sign in to this account. Other accounts are unchanged.")

try:
    blocked = [item["ip"] for item in (api_client.list_blocked_ips(token).get("items") or [])]
except ApiError as exc:
    st.error(exc.detail)
    blocked = []

if not blocked:
    st.caption("None.")
else:
    for ip in blocked:
        left, right = st.columns([3, 1])
        left.write(ip)
        if right.button("Unblock", key=f"unblock-{ip}"):
            try:
                api_client.unblock_ip(token, ip)
                st.rerun()
            except ApiError as exc:
                st.error(exc.detail)

with st.form("block-ip"):
    manual_ip = st.text_input("Block an IP")
    if st.form_submit_button("Block"):
        try:
            api_client.block_ip(token, manual_ip.strip())
            st.rerun()
        except ApiError as exc:
            st.error(exc.detail)

st.divider()
st.subheader("Login history")

try:
    payload = api_client.login_history(token, limit=30)
    rows = payload.get("items") or []
except ApiError as exc:
    st.error(exc.detail)
    rows = []

if not rows:
    st.caption("No events yet.")
else:
    seen: set[str] = set()
    for item in rows:
        ip = item.get("ip") or ""
        cols = st.columns([3, 2, 1, 1])
        cols[0].write(str(item.get("created_at") or ""))
        cols[1].write(ip)
        cols[2].write("ok" if item.get("success") else "fail")
        if ip and ip not in seen and ip not in blocked:
            seen.add(ip)
            if cols[3].button("Block", key=f"block-hist-{ip}"):
                try:
                    api_client.block_ip(token, ip)
                    st.rerun()
                except ApiError as exc:
                    st.error(exc.detail)
        else:
            seen.add(ip)
