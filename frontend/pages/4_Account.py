"""Current user, login history, and per-account blocked IPs."""

import logging
import time

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

st.divider()
st.subheader("SMS two-factor")
st.caption("Optional. After you bind a phone, sign-in asks for an SMS code. Locally the code is in the API log.")


def clear_phone_otp_state() -> None:
    for key in (
        "phone_otp_hint",
        "phone_otp_code",
        "phone_otp_sent_at",
        "phone_otp_expires_at",
        "phone_otp_attempts",
        "phone_otp_verified",
        "phone_otp_error",
        "phone_otp_success",
    ):
        st.session_state.pop(key, None)
    


def phone_otp_remaining_seconds() -> int:
    expires_at = float(st.session_state.get("phone_otp_expires_at") or 0)
    if not expires_at:
        return 0
    return max(0, int(expires_at - time.time()))


@st.fragment(run_every="1s")
def render_phone_otp_countdown() -> None:
    remaining = phone_otp_remaining_seconds()
    if remaining > 0:
        st.info(f"Code expires in {remaining} seconds...")
        return

    if st.session_state.get("phone_otp_expires_at"):
        clear_phone_otp_state()
        st.warning("Code expired. You can send a new code.")

if user.get("two_factor_enabled"):
    st.write(f"Enabled for {user.get('phone_hint') or 'your phone'}.")
    if st.button("Turn off SMS 2FA"):
        try:
            updated = api_client.disable_2fa(token)
            logging.info(f"Disabled 2FA for user {user.get('username')}")
            logging.info(f"Updated user record: {updated}")
            st.session_state["user"] = updated
            st.rerun()
        except ApiError as exc:
            st.error(exc.detail)
else:
    render_phone_otp_countdown()
    remaining = phone_otp_remaining_seconds()

    with st.form("bind-phone"):
        phone = st.text_input("Mobile number (E.164, e.g. +64211234567)")
        send_code_disabled = remaining > 0
        if st.form_submit_button("Send code", disabled=send_code_disabled):
            try:
                started = api_client.start_phone_2fa(token, phone.strip())
                st.session_state["phone_otp_hint"] = started.get("phone_hint") or ""
                st.session_state["phone_otp_expires_at"] = time.time() + 30
                st.success("Code sent.")
                st.rerun()
            except ApiError as exc:
                st.error(exc.detail)
    if st.session_state.get("phone_otp_hint"):
        with st.form("confirm-phone"):
            code = st.text_input("Verification code")
            if st.form_submit_button("Confirm and enable"):
                try:
                    updated = api_client.confirm_phone_2fa(token, code.strip())
                    st.session_state["user"] = updated
                    st.session_state.pop("phone_otp_hint", None)
                    st.rerun()
                except ApiError as exc:
                    st.error(exc.detail)

if st.button("Sign out"):
    session.sign_out()
    st.success("Signed out.")
    st.rerun()

st.divider()
blocked: list[str] = []
if user.get("is_admin"):
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
else:
    st.subheader("Blocked IPs")
    st.info("Admin access required to view or manage blocked IPs.")

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
