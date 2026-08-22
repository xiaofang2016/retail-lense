"""CSV/Excel upload widget. File bytes go to FastAPI, which writes S3."""


def upload_form() -> None:
    import streamlit as st

    st.file_uploader("Transaction file", type=["csv", "xlsx"])
    st.number_input("Number of segments (k)", min_value=2, max_value=12, value=4)
    st.button("Start analysis")
    # TODO: POST /uploads then show job status
