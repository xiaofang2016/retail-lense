"""Sign in and forgot-password. Uses POST /auth/signin and /users/forgot-password."""

import time

import streamlit as st

from components.style import setup
from services import api_client, session
from services.api_client import ApiError

setup("Sign in")

st.title("Sign in")

if session.signed_in():
    st.write("You are already signed in to the application. Redirecting to the Account page...")
    countdown_notice = st.empty()
    for sec in range(3, 0, -1):
        countdown_notice.info(f"Redirecting in {sec}...")
        time.sleep(1)
    st.switch_page("pages/4_Account.py")
    st.stop()

otp_username = st.session_state.get("otp_username")
if otp_username:
    st.caption(f"Enter the SMS code sent to {st.session_state.get('otp_hint') or 'your phone'}.")
    with st.form("otp"):
        code = st.text_input("Verification code")
        submitted_otp = st.form_submit_button("Verify")
    if submitted_otp:
        try:
            data = api_client.verify_otp(
                otp_username,
                code.strip(),
                remember_me=bool(st.session_state.get("otp_remember")),
            )
            session.save_login(data["access_token"], remember_me=bool(st.session_state.get("otp_remember")))
            st.session_state.pop("otp_username", None)
            st.session_state.pop("otp_hint", None)
            st.session_state.pop("otp_remember", None)
            st.success("Signed in. You can now open the Account page.")
        except ApiError as exc:
            st.error(exc.detail)
        except Exception as exc:
            st.error(str(exc))
    if st.button("Use a different account"):
        st.session_state.pop("otp_username", None)
        st.session_state.pop("otp_hint", None)
        st.session_state.pop("otp_remember", None)
        st.rerun()
    st.stop()

with st.form("signin"):
    username = st.text_input("Email or username")
    password = st.text_input("Password", type="password")
    remember = st.checkbox("Remember me")
    submitted = st.form_submit_button("Sign in")

if submitted:
    try:
        data = api_client.signin(username.strip(), password, remember_me=remember)
        if data.get("status") == "otp_required":
            st.session_state["otp_username"] = username.strip()
            st.session_state["otp_hint"] = data.get("phone_hint") or ""
            st.session_state["otp_remember"] = remember
            st.rerun()
        session.save_login(data["access_token"], remember_me=remember)
        # Let the cookie component finish writing before another Streamlit run.
        st.success("Signed in. redirecting to the Account page...")
        st.switch_page("pages/4_Account.py")
    except ApiError as exc:
        st.error(exc.detail)
    except Exception as exc:
        st.error(str(exc))

st.divider()
with st.expander("Forgot password"):
    st.caption("Use the same email you registered. Inbox: http://localhost:8025")
    email = st.text_input("Account email", key="forgot_email")
    if st.button("Send reset link"):
        try:
            api_client.forgot_password(email.strip())
            st.success("A  reset link was sent.")
        except ApiError as exc:
            st.error(exc.detail)
