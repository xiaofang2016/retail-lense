"""Public About page."""

import streamlit as st

from components.style import setup


setup("About")


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("About Retail Lense")

st.write(
    "Retail Lense is a customer analytics platform designed "
    "to help small and medium retail businesses better "
    "understand their transaction data."
)


# ---------------------------------------------------------
# Our Purpose
# ---------------------------------------------------------

st.divider()

st.subheader("Our Purpose")

st.write(
    "Retail businesses generate valuable information through "
    "everyday transactions, but raw transaction data can be "
    "difficult to interpret and use for decision-making."
)

st.write(
    "Retail Lense brings data analysis, customer segmentation, "
    "and AI-powered advice together to help businesses turn "
    "transaction data into meaningful insights."
)


# ---------------------------------------------------------
# Our Approach
# ---------------------------------------------------------

st.subheader("Our Approach")

st.write(
    "Retail Lense combines business analytics, statistical "
    "analysis, machine learning, and artificial intelligence "
    "to understand customer behaviour and business performance."
)

col1, col2 = st.columns(2)

with col1:

    st.markdown("### Data & Machine Learning")

    st.write(
        "Transaction data is processed through a structured "
        "analysis pipeline. RFM analysis and K-Means clustering "
        "are used to identify meaningful customer segments."
    )


with col2:

    st.markdown("### AI-Powered Advice")

    st.write(
        "Key analytical results and numerical insights are used "
        "to generate written business advice through a "
        "Language Model."
    )


# ---------------------------------------------------------
# Our Team
# ---------------------------------------------------------

st.divider()

st.subheader("Our Team")

st.write(
    "Retail Lense is developed by a multidisciplinary team "
    "covering infrastructure, security, machine learning, "
    "backend, and frontend development."
)


team_col1, team_col2, team_col3 = st.columns(3)


with team_col1:

    st.markdown("### Xiao Yuqun")

    st.markdown("**Infrastructure**")

    st.write(
        "Responsible for cloud infrastructure, deployment, "
        "and application environment management."
    )


with team_col2:

    st.markdown("### SM Farhan")

    st.markdown("**Infrastructure Security**")

    st.write(
        "Responsible for security, authentication, access "
        "control, and protection of application resources."
    )


with team_col3:

    st.markdown("### Tahreem Tahir")

    st.markdown("**ML Developer**")

    st.write(
        "Responsible for data processing, RFM analysis, "
        "K-Means clustering, and the machine learning pipeline."
    )


team_col4, team_col5 = st.columns(2)


with team_col4:

    st.markdown("### Arya Dhuri")

    st.markdown("**Backend Developer**")

    st.write(
        "Responsible for APIs, backend services, and "
        "integration with data processing and storage."
    )


with team_col5:

    st.markdown("### Ei Thae Thae Naing")

    st.markdown("**Frontend Developer**")

    st.write(
        "Responsible for the Streamlit interface, navigation, "
        "data upload, analysis library, and report visualisation."
    )


# ---------------------------------------------------------
# Technology
# ---------------------------------------------------------

st.divider()

st.subheader("Technology")

st.write(
    "Retail Lense combines web development, data analytics, "
    "machine learning, cloud infrastructure, and artificial "
    "intelligence technologies."
)


tech_col1, tech_col2, tech_col3 = st.columns(3)


with tech_col1:

    st.markdown("### Application")

    st.write(
        "Python\n\n"
        "Streamlit\n\n"
        "FastAPI"
    )


with tech_col2:

    st.markdown("### Data & AI")

    st.write(
        "RFM Analysis\n\n"
        "K-Means Clustering\n\n"
        "OpenAI API"
    )


with tech_col3:

    st.markdown("### Cloud & Storage")

    st.write(
        "AWS\n\n"
        "Docker\n\n"
        "DynamoDB"
    )


# ---------------------------------------------------------
# Privacy
# ---------------------------------------------------------

st.divider()

st.subheader("Privacy")

st.write(
    "Retail Lense is designed with privacy and responsible "
    "handling of user information in mind."
)

if st.button(
    "View Data Privacy Policy",
    use_container_width=True,
):

    st.switch_page(
        "pages/10_Data_Privacy.py"
    )


# ---------------------------------------------------------
# Project
# ---------------------------------------------------------

st.divider()

st.subheader("About This Project")

st.write(
    "Retail Lense is developed as a cloud-hosted group "
    "software project combining web development, data "
    "analytics, machine learning, artificial intelligence, "
    "and cloud technologies."
)


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    "Retail Lense — Turning transaction data into meaningful insights."
)