import streamlit as st

from services import session


# Pages call session.prepare() from setup(). Do not restore sessions here:
# main.py runs before st.navigation and cannot rerun the sidebar after a cookie
# restore without racing the selected page.
signed_in = bool(st.session_state.get("access_token"))


# ---------------------------------------------------------
# Public pages
# ---------------------------------------------------------

home_page = st.Page(
    "app.py",
    title="Home",
    icon="🏠",
)

reference_page = st.Page(
    "pages/5_Reference.py",
    title="Reference Analysis",
    icon="📊",
)

privacy_page = st.Page(
    "pages/10_Data_Privacy.py",
    title="Data Privacy Policy",
    icon="🔒",
)

about_page = st.Page(
    "pages/7_About.py",
    title="About",
    icon="ℹ️",
)


# ---------------------------------------------------------
# Authentication pages
# ---------------------------------------------------------

login_page = st.Page(
    "pages/1_Login.py",
    title="Sign In",
    icon="🔐",
    visibility="hidden" if signed_in else "visible",
)

signup_page = st.Page(
    "pages/2_Sign_Up.py",
    title="Sign Up",
    icon="📝",
    visibility="hidden" if signed_in else "visible",
)

reset_password_page = st.Page(
    "pages/3_Reset_Password.py",
    title="Reset Password",
    icon="🔑",
    visibility="hidden",
)


# ---------------------------------------------------------
# Protected pages
# ---------------------------------------------------------

account_page = st.Page(
    "pages/4_Account.py",
    title="Account",
    icon="👤",
    visibility="visible" if signed_in else "hidden",
)

upload_page = st.Page(
    "pages/6_Upload.py",
    title="Generate your own Report",
    icon="📤",
    visibility="visible" if signed_in else "hidden",
)

analysis_library_page = st.Page(
    "pages/8_Analysis_Library.py",
    title="Analysis Library",
    icon="📚",
    visibility="visible" if signed_in else "hidden",
)

analysis_report_page = st.Page(
    "pages/9_Analysis_Report.py",
    title="Analysis Report",
    icon="📄",
    visibility="hidden",
)


# ---------------------------------------------------------
# Register ALL pages
#
# Hidden pages remain registered so st.switch_page()
# can navigate to them.
# ---------------------------------------------------------

pages = [
    home_page,
    login_page,
    signup_page,
    reset_password_page,
    account_page,
    reference_page,
    upload_page,
    analysis_library_page,
    analysis_report_page,
    privacy_page,
    about_page,
]


pg = st.navigation(pages)
pg.run()