"""Create an account. Uses POST /auth/register."""

import time

import streamlit as st

from components.captcha import captcha, refresh_captcha
from components.style import setup
from services import api_client, session
from services.api_client import ApiError


setup("Sign up")

st.title("Create an account")


# ---------------------------------------------------------
# Already signed in
# ---------------------------------------------------------

if session.signed_in():
    st.write(
        "You are already signed in to the application. "
        "Redirecting to the Account page..."
    )

    countdown_notice = st.empty()

    for sec in range(3, 0, -1):
        countdown_notice.info(
            f"Redirecting in {sec}..."
        )
        time.sleep(1)

    st.switch_page("pages/4_Account.py")
    st.stop()


# ---------------------------------------------------------
# Sign-up form
# ---------------------------------------------------------

with st.form("register"):
    full_name = st.text_input(
        "Full name"
    )

    username = st.text_input(
        "Username"
    )

    email = st.text_input(
        "Email"
    )

    password = st.text_input(
        "Password",
        type="password",
    )

    password_confirm = st.text_input(
        "Confirm password",
        type="password",
    )

    # -----------------------------------------------------
    # Display CAPTCHA error close to CAPTCHA
    # -----------------------------------------------------

    captcha_error = st.session_state.pop(
        "signup_captcha_error",
        None,
    )

    if captcha_error:
        st.error(captcha_error)

    # -----------------------------------------------------
    # CAPTCHA verification
    # -----------------------------------------------------

    captcha_valid, captcha_expired = captcha(
        "signup"
    )

    # -----------------------------------------------------
    # Create account button
    # -----------------------------------------------------

    submitted = st.form_submit_button(
        "Create account",
        use_container_width=True,
    )


# ---------------------------------------------------------
# Process registration
# ---------------------------------------------------------

if submitted:

    # -----------------------------------------------------
    # CAPTCHA expired
    # -----------------------------------------------------

    if captcha_expired:
        st.session_state[
            "signup_captcha_error"
        ] = (
            "CAPTCHA expired. "
            "Please enter the new CAPTCHA."
        )

        refresh_captcha("signup")
        st.rerun()

    # -----------------------------------------------------
    # CAPTCHA incorrect
    # -----------------------------------------------------

    if not captcha_valid:
        st.session_state[
            "signup_captcha_error"
        ] = (
            "Incorrect CAPTCHA. "
            "Please enter the new CAPTCHA."
        )

        refresh_captcha("signup")
        st.rerun()

    # -----------------------------------------------------
    # CAPTCHA passed
    # Continue with registration
    # -----------------------------------------------------

    try:
        api_client.register(
            email=email.strip(),
            username=username.strip(),
            full_name=full_name.strip(),
            password=password,
            password_confirm=password_confirm,
        )

        st.success(
            "Account created. "
            "Sign in from the sidebar."
        )

        # Generate a fresh CAPTCHA so the successful
        # CAPTCHA cannot be reused.
        refresh_captcha("signup")

    except ApiError as exc:
        st.error(exc.detail)

    except Exception as exc:
        st.error(str(exc))