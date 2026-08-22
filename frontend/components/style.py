"""Shared Streamlit chrome: narrow layout, muted type."""

import streamlit as st

from services import session

_CSS = """
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {max-width: 640px; padding-top: 3rem; padding-bottom: 4rem;}
    h1 {font-size: 1.5rem; font-weight: 600; letter-spacing: -0.03em; margin-bottom: 0.35rem;}
    p, .stCaption, .stMarkdown {color: #444;}
    div[data-testid="stSidebar"] {background: #fafafa;}
</style>
"""


def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} · Retail Lense", layout="centered")
    st.markdown(_CSS, unsafe_allow_html=True)
    user = session.current_user()
    if user:
        st.sidebar.caption(user.get("email") or user.get("username") or "")
    else:
        st.sidebar.caption("Not signed in")
