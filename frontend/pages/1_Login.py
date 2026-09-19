"""Sign in and forgot-password.

Uses POST /auth/signin and /users/forgot-password.
"""

import logging
import time

import streamlit as st

from components.captcha import captcha, refresh_captcha
from components.style import setup
from services import api_client, session
from services.api_client import ApiError


logger = logging.getLogger(__name__)

setup("Sign in")
st.title("Sign in")


def _complete_login(
    access_token: str,
    remember_me: bool,
    refresh_token_value: str | None = None,
) -> None:
    session.save_login(
        access_token,
        remember_me=remember_me,
        refresh_token_value=refresh_token_value,
    )

    st.success("Signed in. Redirecting to the Account page...")
    st.switch_page("pages/4_Account.py")


if session.signed_in():
    st.write(
        "You are already signed in to the application. "
        "Redirecting to the Account page..."
    )

    countdown_notice = st.empty()

    for sec in range(3, 0, -1):
        countdown_notice.info(f"Redirecting in {sec}...")
        time.sleep(1)

    st.switch_page("pages/4_Account.py")
    st.stop()


otp_username = st.session_state.get("otp_username")

if otp_username:
    st.caption(
        f"Enter the SMS code sent to "
        f"{st.session_state.get('otp_hint') or 'your phone'}."
    )

    with st.form("otp"):
        code = st.text_input("Verification code")
        submitted_otp = st.form_submit_button("Verify")

    if submitted_otp:
        remember_me = bool(st.session_state.get("otp_remember"))

        try:
            data = api_client.verify_otp(
                otp_username,
                code.strip(),
                remember_me=remember_me,
            )

            st.session_state.pop("otp_username", None)
            st.session_state.pop("otp_hint", None)
            st.session_state.pop("otp_remember", None)

            _complete_login(
                data["access_token"],
                remember_me=remember_me,
                refresh_token_value=data.get("refresh_token"),
            )

        except ApiError as exc:
            st.error(exc.detail)

        except Exception as exc:
            logger.exception("Unexpected OTP verification error")
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

    captcha_error = st.session_state.pop(
        "signin_captcha_error",
        None,
    )

    if captcha_error:
        st.error(captcha_error)

    captcha_valid, captcha_expired = captcha("signin")

    submitted = st.form_submit_button(
        "Sign in",
        use_container_width=True,
    )


if submitted:
    if captcha_expired:
        st.session_state["signin_captcha_error"] = (
            "CAPTCHA expired. Please enter the new CAPTCHA."
        )
        refresh_captcha("signin")
        st.rerun()

    if not captcha_valid:
        st.session_state["signin_captcha_error"] = (
            "Incorrect CAPTCHA. Please enter the new CAPTCHA."
        )
        refresh_captcha("signin")
        st.rerun()

    try:
        data = api_client.signin(
            username.strip(),
            password,
            remember_me=remember,
        )

        logger.info("Sign-in response received for %s", username.strip())

        if data.get("status") == "otp_required":
            st.session_state["otp_username"] = username.strip()
            st.session_state["otp_hint"] = data.get("phone_hint") or ""
            st.session_state["otp_remember"] = remember
            st.rerun()

        _complete_login(
            data["access_token"],
            remember_me=remember,
            refresh_token_value=data.get("refresh_token"),
        )

    except ApiError as exc:
        st.error(exc.detail)

    except Exception as exc:
        logger.exception("Unexpected sign-in error")
        st.error(str(exc))


st.divider()

with st.expander("Forgot password"):
    st.caption(
        "Use the same email you registered. "
        "Inbox: http://localhost:8025"
    )

    email = st.text_input("Account email", key="forgot_email")

    if st.button("Send reset link"):
        try:
            api_client.forgot_password(email.strip())
            st.success("A reset link was sent.")

        except ApiError as exc:
            st.error(exc.detail)