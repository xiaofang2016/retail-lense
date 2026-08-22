"""Private upload page. Offers a CSV template matching the required schema."""

from pathlib import Path

import streamlit as st

from components.style import setup
from services import session

setup("Upload")

TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "assets" / "transactions_template.csv"

st.title("Upload")
st.caption(
    "Required columns: InvoiceNo, StockCode, Description, Quantity, "
    "InvoiceDate, UnitPrice, CustomerID. Country is optional."
)

st.download_button(
    label="Download CSV template",
    data=TEMPLATE_PATH.read_bytes(),
    file_name="retail_lense_transactions_template.csv",
    mime="text/csv",
)

if not session.signed_in():
    st.write("Sign in to upload a file.")
    st.stop()

st.write("Analysis API is not connected yet.")
