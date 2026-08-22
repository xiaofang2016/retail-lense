"""Home: product line and account status."""

import streamlit as st

from components.style import setup
from services import session

setup("Home")

st.title("Retail Lense")
st.caption("Customer segments from your transactions. RFM, K-Means, written advice.")

user = session.current_user()
if user:
    st.write(f"Signed in as **{user.get('full_name') or user.get('username')}**.")
    if st.button("Sign out"):
        session.sign_out()
        st.rerun()
else:
    st.write("Sign in to upload a file. The public reference report is in the sidebar.")
