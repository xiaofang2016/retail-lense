"""Shared Streamlit chrome: narrow layout, muted type."""
from pathlib import Path

import streamlit as st

from services import session

_CSS = """
<style>
    #MainMenu, footer, header {{
        visibility: hidden;
    }}
    .block-container {{
        width: 100%; max-width: 100%; padding-top: 3rem; padding-bottom: 4rem;padding-left: 4rem; padding-right: 4rem;
    }}

    h1 {{
    font-size: 1.5rem; 
    font-weight: 600; 
    letter-spacing: -0.03em;
    margin-bottom: 0.35rem;
    }}

    p, .stCaption, .stMarkdown {{
        color: #444;
    }}

    div[data-testid="stSidebar"] {{
        background: #fafafa;
    }}

     /* Increase logo size */
    .st-emotion-cache-1wxyy64 {
        height: 3.5rem;
        margin-top: 1.25rem;
    }
</style>
"""




def setup(title: str) -> None:
    st.set_page_config(page_title=f"{title} · Retail Lense", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)

    # Add logo to sidebar
    logo_path = Path(__file__).parent.parent / "assets" / "RT_logo.png"
    if logo_path.exists():
        st.logo(str(logo_path))

    session.prepare()
    user = session.current_user()
    if user:
        st.sidebar.caption(user.get("email") or user.get("username") or "")
    else:
        st.sidebar.caption("Not signed in")
