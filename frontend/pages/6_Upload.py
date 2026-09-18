"""Upload transaction data for customer analysis."""

import pandas as pd
import streamlit as st

from components.style import setup
from services import api_client, session

MAX_UPLOAD_MB = 30
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

setup("Upload Data")


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Generate Your Own Report")

st.write(
    "Turn your retail transaction data into customer insights "
    "using RFM analysis and K-Means segmentation."
)


# ---------------------------------------------------------
# Access control
# ---------------------------------------------------------

# Sign-in is now required: POST /analyses needs a JWT to attribute the upload to a user.
if not session.signed_in():
    st.warning("Please sign in before uploading your data.")

    if st.button("Go to Sign In", use_container_width=True):
        st.switch_page("pages/1_Login.py")

    st.stop()


# ---------------------------------------------------------
# File requirements
# ---------------------------------------------------------

st.subheader("File Requirements")

st.write(
    "Your transaction file must contain the following "
    "required columns:"
)

required_columns = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
]

cols = st.columns(4)

for column, field in zip(cols * 2, required_columns):
    with column:
        st.markdown(f"✓ **{field}**")

st.caption("Optional column: Country")
st.caption(f"Maximum file size: {MAX_UPLOAD_MB}MB")

# ---------------------------------------------------------
# Sample template
# ---------------------------------------------------------

st.subheader("Sample Template")

sample_col1, sample_col2 = st.columns([3, 1])

with sample_col1:
    st.write(
        "Download the sample transaction file to see the "
        "required format before uploading your own data."
    )

with sample_col2:
    st.download_button(
        label="📥 Download Sample",
        data=b"",
        file_name="transactions_sample.csv",
        mime="text/csv",
        disabled=True,
        use_container_width=True,
        help="The sample template will be available when the backend is running.",
    )

st.caption(
    "The sample template is currently unavailable while "
    "the backend is offline."
)


# ---------------------------------------------------------
# Upload transaction file
# ---------------------------------------------------------

st.divider()

st.subheader("Upload Transaction File")

st.write(
    "Choose your transaction data in CSV or Excel format."
)

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["csv", "xlsx"],
    help=(
        "Supported formats: CSV and Excel (.xlsx). "
        "The file must contain all required columns."
    ),
)


# ---------------------------------------------------------
# File validation
# ---------------------------------------------------------

file_valid = False
df = None

if uploaded_file is not None:

    st.success(f"File selected: **{uploaded_file.name}**")

    if uploaded_file.size > MAX_UPLOAD_BYTES:

        st.error(
            f"This file is {uploaded_file.size / (1024 * 1024):.1f}MB, which exceeds "
            f"the {MAX_UPLOAD_MB}MB limit. Please upload a smaller file."
        )

    else:

        try:

            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write(
                f"**Rows:** {len(df):,}  |  "
                f"**Columns:** {len(df.columns)}"
            )

            required = {
                "InvoiceNo",
                "StockCode",
                "Description",
                "Quantity",
                "InvoiceDate",
                "UnitPrice",
                "CustomerID",
            }

            actual_columns = set(df.columns)
            missing_columns = required - actual_columns

            if missing_columns:

                st.error(
                    "The uploaded file is missing the following "
                    "required columns:"
                )

                for column in sorted(missing_columns):
                    st.write(f"- {column}")

            else:

                file_valid = True

                st.success("✓ File structure is valid.")

                with st.expander("Preview transaction data"):

                    # Columns like StockCode can mix numeric and alphanumeric codes
                    # (e.g. 20713 and 85123A), which breaks Streamlit's Arrow-based
                    # rendering unless coerced to a single consistent type first.
                    preview_df = df.head(10).copy()

                    for column in preview_df.select_dtypes(include=["object", "str"]).columns:
                        preview_df[column] = preview_df[column].astype(str)

                    st.dataframe(
                        preview_df,
                        use_container_width=True,
                    )

        except Exception as exc:

            st.error(
                "Unable to read the uploaded file. "
                "Please check that it is a valid CSV or Excel file."
            )

            st.caption(str(exc))

# ---------------------------------------------------------
# Start analysis
# ---------------------------------------------------------

st.divider()

st.subheader("Start Analysis")

st.write(
    "Once your file has been validated, start the analysis "
    "to process your customer data."
)

if st.button(
    "🚀 Start Analysis",
    type="primary",
    use_container_width=True,
):

    if uploaded_file is None:

        st.warning(
            "Please select a transaction file before "
            "starting the analysis."
        )

    elif not file_valid:

        st.error(
            "Please fix the file validation errors "
            "before starting the analysis."
        )

    else:

        file_extension = "xlsx" if uploaded_file.name.lower().endswith(".xlsx") else "csv"
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if file_extension == "xlsx"
            else "text/csv"
        )

        try:
            # Ask FastAPI for a presigned S3 PUT URL + a new analysis_id (POST /analyses).
            created = api_client.create_analysis(
                session.token(), file_extension, uploaded_file.name, uploaded_file.size
            )

            # Upload the raw bytes straight to S3 -- the backend never sees the file body.
            api_client.upload_bytes_to_presigned_url(
                created["upload_url"],
                uploaded_file.getvalue(),
                content_type,
            )

            # Remember the analysis_id so the Report page can poll its status.
            st.session_state["analysis_id"] = created["analysis_id"]

            st.success("Analysis started successfully!")

            st.info(
                "Your transaction data is being processed. "
                "Visit the Analysis Library to check the status "
                "and view your report when it is ready."
            )

            if st.button(
                "📚 Go to Analysis Library",
                use_container_width=True,
            ):
                st.switch_page("pages/8_Analysis_Library.py")

        except api_client.ApiError as exc:
            st.error(f"Could not start the analysis: {exc.detail}")


