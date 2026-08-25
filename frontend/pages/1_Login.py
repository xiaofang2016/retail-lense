"""Sign in and forgot-password. Uses POST /auth/signin and /users/forgot-password."""

import streamlit as st

from components.style import setup
from services import api_client, session
from services.api_client import ApiError

setup("Sign in")

st.title("Sign in")

if session.signed_in():
    st.write("You are already signed in to the application.")
    st.stop()

with st.form("signin"):
    username = st.text_input("Email or username")
    password = st.text_input("Password", type="password")
    remember = st.checkbox("Remember me")
    submitted = st.form_submit_button("Sign in")

if submitted:
    try:
        data = api_client.signin(username.strip(), password, remember_me=remember)
        session.save_login(data["access_token"])
        st.rerun()
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
