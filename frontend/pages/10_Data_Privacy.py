"""Data Privacy Policy page."""

import streamlit as st

from components.style import setup


setup("Data Privacy Policy")


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Data Privacy Policy")

st.write(
    "Retail Lense is designed with reference to New Zealand's Privacy Act 2020 "
    "and its 13 Information Privacy Principles (IPPs). The "
    "entity operating Retail Lense is based in New Zealand. This "
    "applies regardless of where a user or their business is "
    "located."
)


st.caption(
    "This page describes the privacy approach used in the "
    "Retail Lense Platform."
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
    "This policy is governed by the 13 Information Privacy "
    "Principles under the New Zealand Privacy Act 2020, because "
    "Retail Lense is operated by a New Zealand-based entity. "
    "Retail Lense's users are not limited to New Zealand — if you "
    "are located elsewhere, you may have additional or different "
    "privacy rights under your own local laws, and this policy "
    "does not limit or replace those rights."
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
        "We collect personal information only for purposes connected "
        "with operating Retail Lense — creating and authenticating "
        "accounts, running the analysis a user requests, and keeping "
        "the application secure. We do not collect information beyond "
        "what those purposes require."
    )


with st.expander(
    "IPP 2 — Source of personal information"
):

    st.write(
        "Account information (name, username, email, password) is "
        "collected directly from the individual signing up. Customer "
        "information contained in a transaction file is provided by "
        "the uploading user, not collected directly from those "
        "customers by Retail Lense."
    )


with st.expander(
    "IPP 3 — Collection of information"
):

    st.write(
        "This policy and the consent checkbox on the sign-up page "
        "inform users what information is collected and why, before "
        "an account is created."
    )


with st.expander(
    "IPP 4 — Manner of collection"
):

    st.write(
        "Information is collected through the application's own "
        "forms and upload feature — account details typed in by the "
        "user, and transaction files the user chooses to upload. No "
        "information is collected through other means."
    )


with st.expander(
    "IPP 5 — Storage and security"
):

    st.write(
        "Passwords are hashed and never stored in plain text. Data in "
        "transit is encrypted (HTTPS/TLS). Access to stored data is "
        "restricted by account authentication, and infrastructure "
        "access is limited to what each part of the system needs to "
        "function (see Section 8)."
    )


with st.expander(
    "IPP 6 — Access to personal information"
):

    st.write(
        "A signed-in user can view their own account details and "
        "analysis history in the application at any time. Requests "
        "for other information held about an individual can be made "
        "by contacting the project team."
    )


with st.expander(
    "IPP 7 — Correction of personal information"
):

    st.write(
        "A user can update their account details from the Account "
        "page. Corrections to other information can be requested by "
        "contacting the project team."
    )


with st.expander(
    "IPP 8 — Accuracy before use"
):

    st.write(
        "Analysis results are generated directly from the data a "
        "user uploads, so their accuracy depends on the accuracy of "
        "that upload. Retail Lense validates that a file contains the "
        "required columns before processing it, and rejects files "
        "that do not."
    )


with st.expander(
    "IPP 9 — Retention of personal information"
):

    st.write(
        "The raw transaction file a user uploads is deleted "
        "automatically once its analysis report has been generated — "
        "it is not needed after that point and is not kept. The "
        "generated report and account information are kept until the "
        "user deletes the analysis or the account, respectively (see "
        "Section 9)."
    )


with st.expander(
    "IPP 10 — Limits on use"
):

    st.write(
        "Uploaded transaction data is used only to produce the "
        "analysis report the uploading user requested. It is not used "
        "for any other purpose, and is not shared with or used to "
        "benefit any other account."
    )


with st.expander(
    "IPP 11 — Limits on disclosure"
):

    st.write(
        "Personal information is not disclosed to third parties, "
        "except where sending a limited set of numerical analysis "
        "results to the AI service used to generate written advice "
        "(see Section 7), or where disclosure is required by law."
    )


with st.expander(
    "IPP 12 — Disclosure outside New Zealand"
):

    st.write(
        "Retail Lense's infrastructure and the AI service it uses may "
        "process data outside New Zealand. Only aggregated analysis "
        "metrics are sent to the AI service — never raw transaction "
        "or customer data (see Section 7)."
    )


with st.expander(
    "IPP 13 — Unique identifiers"
):

    st.write(
        "Retail Lense assigns an internal account ID and analysis ID "
        "to each user and analysis. These identifiers are used only "
        "within the application, to link a user to their own accounts "
        "and analyses, and are not used as identifiers outside it."
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
    "Retail Lense uses OpenAI's API to generate the written business "
    "advice shown on an analysis report."
)

st.write(
    "Only aggregated, numerical analysis results are sent to OpenAI — "
    "for example, customer counts, average order value, and per-segment "
    "averages for Recency, Frequency, and Monetary value. The raw "
    "transaction file, and any individual customer-identifying "
    "information within it, is never sent to OpenAI."
)

st.write(
    "OpenAI processes this information under its own API data-usage "
    "terms and does not use API data to train its models."
)


# ---------------------------------------------------------
# Data security
# ---------------------------------------------------------

st.subheader("8. Data Security")

st.write(
    "Retail Lense applies the following security measures to protect "
    "user information and analysis data:"
)

st.markdown(
    """
- Passwords are hashed and account sessions use signed, expiring login tokens
- Repeated failed sign-in attempts are automatically rate-limited and, after enough failures, temporarily blocked
- Every account only has access to its own analyses and uploaded files
- Uploaded files are transferred and stored using a temporary, single-use upload link rather than a permanently open channel
- Data in transit between a user's browser and Retail Lense is encrypted (HTTPS)
- Access to the underlying cloud infrastructure is restricted to what each system component needs to function
"""
)


# ---------------------------------------------------------
# Data retention and deletion
# ---------------------------------------------------------

st.subheader("9. Data Retention and Deletion")

st.markdown(
    """
- **Raw uploaded files** are deleted automatically once their analysis report has been generated. They are not kept afterward.
- **Analysis reports** (charts, segments, and AI-generated advice) are kept until the user deletes that analysis from the Analysis Library.
- **Account information** is kept for as long as the account exists.
"""
)

st.write(
    "Users can delete an individual analysis at any time from the "
    "Analysis Library, which also removes its stored report from "
    "Retail Lense's storage."
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