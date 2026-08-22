"""Create an account. Uses POST /auth/register."""

import streamlit as st

from components.style import setup
from services import api_client
from services.api_client import ApiError

setup("Sign up")

st.title("Create an account")

with st.form("register"):
    full_name = st.text_input("Full name")
    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    password_confirm = st.text_input("Confirm password", type="password")
    submitted = st.form_submit_button("Create account")

if submitted:
    try:
        api_client.register(
            email=email.strip(),
            username=username.strip(),
            full_name=full_name.strip(),
            password=password,
            password_confirm=password_confirm,
        )
        st.success("Account created. Sign in from the sidebar.")
    except ApiError as exc:
        st.error(exc.detail)
    except Exception as exc:
        st.error(str(exc))
