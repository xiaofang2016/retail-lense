"""Set a new password from an email token. Uses POST /users/reset-password."""

import streamlit as st

from components.style import setup
from services import api_client
from services.api_client import ApiError

setup("Reset password")

st.title("Reset password")
st.caption("Open the email link, or paste the token from that message.")

query_token = st.query_params.get("token", "")

with st.form("reset"):
    email = st.text_input("Email")
    token = st.text_input("Reset token", value=query_token or "")
    password = st.text_input("New password", type="password")
    password_confirm = st.text_input("Confirm password", type="password")
    submitted = st.form_submit_button("Update password")

if submitted:
    try:
        api_client.reset_password(token.strip(), email.strip(), password, password_confirm)
        st.success("Password updated. Sign in with the new password.")
    except ApiError as exc:
        st.error(exc.detail)
    except Exception as exc:
        st.error(str(exc))
