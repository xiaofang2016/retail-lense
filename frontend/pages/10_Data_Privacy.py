"""Data Privacy Policy page."""

import streamlit as st

from components.style import setup


setup("Data Privacy Policy")


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Data Privacy Policy")

st.write(
    "Retail Lense is designed with reference to New Zealand's "
    "Privacy Act 2020 and its 13 Information Privacy Principles "
    "(IPPs)."
)


st.caption(
    "This page describes the privacy approach used in the "
    "Retail Lense project."
)


# ---------------------------------------------------------
# Introduction
# ---------------------------------------------------------

st.divider()

st.subheader("1. Introduction")

st.write(
    "Retail Lense processes account information and uploaded "
    "transaction data to provide customer and business "
    "analytics."
)

st.write(
    "We aim to handle personal information responsibly and "
    "apply privacy and security measures throughout the "
    "application."
)

st.info(
    "Retail Lense has been designed with reference to the "
    "13 Information Privacy Principles under the New Zealand "
    "Privacy Act 2020."
)


# ---------------------------------------------------------
# Information we handle
# ---------------------------------------------------------

st.subheader("2. Information We Handle")

st.write(
    "Depending on how the platform is used, Retail Lense "
    "may handle the following information:"
)

st.markdown(
    """
- Account and authentication information
- Information required to identify a user's account
- Uploaded transaction data
- Customer-related information contained in uploaded files
- Analysis results generated from uploaded data
- Analysis history and report information
- Information required to operate and secure the application
"""
)


# ---------------------------------------------------------
# Purpose of collection
# ---------------------------------------------------------

st.subheader("3. Why Information Is Collected")

st.write(
    "Information is handled only for purposes connected with "
    "providing and operating Retail Lense."
)

st.markdown(
    """
This includes:

- Creating and managing user accounts
- Authenticating users
- Processing uploaded transaction data
- Performing business and customer analysis
- Generating analysis reports
- Providing personalised business insights
- Maintaining analysis history
- Supporting application security and operation
"""
)


# ---------------------------------------------------------
# Information Privacy Principles
# ---------------------------------------------------------

st.divider()

st.subheader(
    "4. Information Privacy Principles"
)

st.write(
    "The Retail Lense privacy approach is aligned with the "
    "following 13 Information Privacy Principles established "
    "under the New Zealand Privacy Act 2020."
)


with st.expander(
    "IPP 1 — Purpose of collection"
):

    st.write(
        "Personal information should be collected for a "
        "lawful purpose connected with the functions or "
        "activities of the application and should be "
        "necessary for that purpose."
    )


with st.expander(
    "IPP 2 — Source of personal information"
):

    st.write(
        "Where appropriate, personal information should be "
        "collected directly from the individual concerned."
    )


with st.expander(
    "IPP 3 — Collection of information"
):

    st.write(
        "Individuals should be informed about the collection "
        "of their personal information and relevant matters "
        "associated with that collection."
    )


with st.expander(
    "IPP 4 — Manner of collection"
):

    st.write(
        "Personal information should be collected fairly and "
        "in a manner that does not intrude unreasonably on "
        "the individual's personal affairs."
    )


with st.expander(
    "IPP 5 — Storage and security"
):

    st.write(
        "Reasonable safeguards should be applied to protect "
        "personal information against loss, unauthorised "
        "access, use, modification, disclosure, or other misuse."
    )


with st.expander(
    "IPP 6 — Access to personal information"
):

    st.write(
        "Individuals have rights relating to access to "
        "personal information held about them, subject to "
        "the requirements and exceptions of the Privacy Act."
    )


with st.expander(
    "IPP 7 — Correction of personal information"
):

    st.write(
        "Individuals have rights to request correction of "
        "personal information that is held about them."
    )


with st.expander(
    "IPP 8 — Accuracy before use"
):

    st.write(
        "Reasonable steps should be taken to ensure personal "
        "information is accurate, complete, relevant, and "
        "up to date before it is used."
    )


with st.expander(
    "IPP 9 — Retention of personal information"
):

    st.write(
        "Personal information should not be retained for "
        "longer than required for the purposes for which "
        "it may lawfully be used."
    )


with st.expander(
    "IPP 10 — Limits on use"
):

    st.write(
        "Personal information should generally only be used "
        "for the purpose for which it was collected, subject "
        "to the exceptions provided by the Privacy Act."
    )


with st.expander(
    "IPP 11 — Limits on disclosure"
):

    st.write(
        "Personal information should generally only be "
        "disclosed for appropriate purposes and in accordance "
        "with the requirements of the Privacy Act."
    )


with st.expander(
    "IPP 12 — Disclosure outside New Zealand"
):

    st.write(
        "Personal information disclosed outside New Zealand "
        "should be handled in accordance with the applicable "
        "requirements of the Privacy Act."
    )


with st.expander(
    "IPP 13 — Unique identifiers"
):

    st.write(
        "Unique identifiers should only be assigned and used "
        "where appropriate and in accordance with the "
        "requirements of the Privacy Act."
    )


# ---------------------------------------------------------
# User uploaded data
# ---------------------------------------------------------

st.divider()

st.subheader("5. User-Uploaded Transaction Data")

st.write(
    "Users may upload transaction data in CSV or Excel format "
    "for analysis."
)

st.write(
    "Uploaded data may contain customer-related information. "
    "Users should ensure that they have the appropriate "
    "authority to upload and process the information they "
    "provide to the platform."
)

st.write(
    "The data is used to perform the analysis requested by "
    "the user and to produce the associated analysis results."
)


# ---------------------------------------------------------
# Access control
# ---------------------------------------------------------

st.subheader("6. Access and Privacy")

st.write(
    "Analysis data and results are intended to be private to "
    "the account that owns the analysis."
)

st.write(
    "Users should not share their account credentials or "
    "provide access to their account to unauthorised people."
)


# ---------------------------------------------------------
# AI / Language Model
# ---------------------------------------------------------

st.subheader("7. AI-Powered Analysis")

st.write(
    "Retail Lense uses a Language Model to generate written "
    "business advice from analysis results and key numerical "
    "insights."
)

st.write(
    "The information sent to an external AI service should "
    "be limited to the information required to generate the "
    "requested analysis or recommendation."
)

st.warning(
    "The final implementation should document the specific "
    "information sent to the AI service, the service provider, "
    "and the applicable data-handling arrangements."
)


# ---------------------------------------------------------
# Data security
# ---------------------------------------------------------

st.subheader("8. Data Security")

st.write(
    "Retail Lense is designed to apply reasonable security "
    "measures to protect user information and analysis data."
)

st.write(
    "Security controls include appropriate authentication, "
    "access control, secure application design, and protection "
    "of stored data as implemented by the application."
)


# ---------------------------------------------------------
# Data retention and deletion
# ---------------------------------------------------------

st.subheader("9. Data Retention and Deletion")

st.write(
    "Personal information should only be retained for as "
    "long as it is required for the purposes for which it "
    "may lawfully be used."
)

st.write(
    "Users may delete analysis records through the Analysis "
    "Library where the deletion functionality is available."
)


# ---------------------------------------------------------
# Privacy breaches
# ---------------------------------------------------------

st.subheader("10. Privacy Breaches")

st.write(
    "Retail Lense will follow the applicable requirements "
    "for responding to privacy breaches."
)

st.write(
    "Where a privacy breach meets the relevant threshold "
    "for notification, the applicable notification "
    "requirements under the Privacy Act 2020 will be followed."
)


# ---------------------------------------------------------
# Changes to this policy
# ---------------------------------------------------------

st.subheader("11. Changes to This Policy")

st.write(
    "This policy may be updated when the Retail Lense "
    "application, its data practices, or applicable privacy "
    "requirements change."
)


# ---------------------------------------------------------
# Reference
# ---------------------------------------------------------

st.divider()

st.subheader("12. Reference")

st.write(
    "This privacy approach is based on the Information "
    "Privacy Principles in the New Zealand Privacy Act 2020."
)

st.markdown(
    "For the official legislation, see the "
    "[New Zealand Privacy Act 2020](https://www.legislation.govt.nz/act/public/2020/31/en/latest/)."
)


# ---------------------------------------------------------
# Back to About
# ---------------------------------------------------------

st.divider()

if st.button(
    "← Back to About",
    use_container_width=True,
):

    st.switch_page(
        "pages/7_About.py"
    )