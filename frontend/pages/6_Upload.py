"""Private upload page. CSV template is served from S3 via the API."""

import streamlit as st

from components.style import setup
from services import api_client, session
from services.api_client import ApiError

setup("Upload")

st.title("Upload")
st.caption(
    "Required columns: InvoiceNo, StockCode, Description, Quantity, "
    "InvoiceDate, UnitPrice, CustomerID. Country is optional. "
    "Template is the transactions_sample file in S3."
)

sample_bytes: bytes | None = None
try:
    sample_bytes = api_client.transactions_sample()
except ApiError as exc:
    st.error(f"Could not load the S3 sample: {exc.detail}")
except Exception as exc:
    st.error(str(exc))

if sample_bytes:
    st.download_button(
        label="Download CSV sample",
        data=sample_bytes,
        file_name="transactions_sample.csv",
        mime="text/csv",
    )

if not session.signed_in():
    st.write("Sign in to upload a file.")
    st.stop()

st.write("Analysis API is not connected yet.")
