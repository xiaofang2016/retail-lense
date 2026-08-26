import streamlit as st


pages = [
    st.Page(
        "app.py",
        title="Home",
        icon="🏠",
    ),
    st.Page(
        "pages/1_Login.py",
        title="Sign In",
        icon="🔐",
    ),
    st.Page(
        "pages/2_Sign_Up.py",
        title="Sign Up",
        icon="📝",
    ),
    st.Page(
        "pages/3_Reset_Password.py",
        title="Reset Password",
        icon="🔑",
    ),
    st.Page(
        "pages/4_Account.py",
        title="Account",
        icon="👤",
    ),
    st.Page(
        "pages/5_Reference.py",
        title="Reference Analysis",
        icon="📊",
    ),
    st.Page(
        "pages/6_Upload.py",
        title="Upload Data",
        icon="📤",
    ),
    st.Page(
        "pages/7_About.py",
        title="About",
        icon="ℹ️",
    ),
]

pg = st.navigation(pages)

pg.run()