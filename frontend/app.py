"""Retail Lense home page."""

 
import streamlit as st

from components.style import setup
from services import session



setup("Home")


# ---------------------------------------------------------
# Hero section
# ---------------------------------------------------------

st.title("Retail Lense")

st.header("Understand Your Customers. Make Smarter Decisions.")

st.write(
    "Turn your retail transaction data into meaningful customer "
    "insights using business analytics, RFM analysis, K-Means "
    "segmentation and AI-powered recommendations."
)

st.write("")

col1, col2 = st.columns([1, 1])

with col1:
    if st.button(
        "Explore Reference Analysis",
        use_container_width=True,
    ):
        st.switch_page("pages/5_Reference.py")

with col2:
    if st.button(
        "Analyse My Data",
        use_container_width=True,
    ):
        if session.signed_in():
            st.switch_page("pages/6_Upload.py")
        else:
            st.info("Please sign in before uploading your data.")


st.divider()


# ---------------------------------------------------------
# Why Retail Lense
# ---------------------------------------------------------

st.subheader("Why Retail Lense?")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📊")
    st.markdown("**Business Metrics**")
    st.write(
        "Understand revenue, invoices, customers and "
        "average order value."
    )

with col2:
    st.markdown("### 👥")
    st.markdown("**Customer Insights**")
    st.write(
        "Discover patterns in your customer purchasing "
        "behaviour."
    )

with col3:
    st.markdown("### 🎯")
    st.markdown("**RFM & K-Means**")
    st.write(
        "Identify valuable customer groups using RFM "
        "analysis and K-Means clustering."
    )

with col4:
    st.markdown("### ✨")
    st.markdown("**AI-Powered Advice**")
    st.write(
        "Receive written recommendations based on "
        "your analysis results."
    )


st.divider()


# ---------------------------------------------------------
# How it works
# ---------------------------------------------------------

st.subheader("How It Works")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 01")
    st.markdown("**Upload**")
    st.write(
        "Upload your transaction data in CSV or Excel format."
    )

with col2:
    st.markdown("### 02")
    st.markdown("**Analyse**")
    st.write(
        "Our pipeline cleans and processes your transaction data."
    )

with col3:
    st.markdown("### 03")
    st.markdown("**Segment**")
    st.write(
        "RFM analysis and K-Means identify customer segments."
    )

with col4:
    st.markdown("### 04")
    st.markdown("**Get Insights**")
    st.write(
        "Receive visual analysis and AI-powered business advice."
    )


st.divider()


# ---------------------------------------------------------
# Account status
# ---------------------------------------------------------

user = session.current_user()

if user:
    st.caption(
        f"Signed in as "
        f"**{user.get('full_name') or user.get('username')}**"
    )

    if st.button("Sign out"):
        session.sign_out()
        st.success("Signed out.")
        st.rerun()
else:
    st.caption(
        "Not signed in. Sign in to upload and analyse your own data."
    )