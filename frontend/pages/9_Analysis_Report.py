"""Interactive customer analysis report."""

import streamlit as st

from components.report_view import render_report
from components.style import setup
from services import api_client, session

setup("Analysis Report")

# ---------------------------------------------------------
# Access control
# ---------------------------------------------------------

if not session.signed_in():
    st.warning("Please sign in to view your analysis reports.")

    if st.button("Go to Sign In", use_container_width=True):
        st.switch_page("pages/1_Login.py")

    st.stop()


# ---------------------------------------------------------
# Resolve which analysis to show
# ---------------------------------------------------------

# Query param survives a browser refresh; session_state covers both a fresh upload
# (pages/6_Upload.py sets "analysis_id" directly) and a click from the Library
# (pages/8_Analysis_Library.py sets "selected_analysis").
selected_analysis = st.session_state.get("selected_analysis")

analysis_id = (
    st.query_params.get("analysis_id")
    or st.session_state.get("analysis_id")
    or (selected_analysis.get("id") if selected_analysis else None)
)

if not analysis_id:
    st.warning("Please select an analysis from the Analysis Library.")

    if st.button("Go to Analysis Library"):
        st.switch_page("pages/8_Analysis_Library.py")

    st.stop()

st.session_state["analysis_id"] = analysis_id


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

back_col, _ = st.columns([1, 5])

with back_col:
    if st.button("← Back to Analysis Library"):
        st.switch_page("pages/8_Analysis_Library.py")


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Customer Analysis")

if selected_analysis:
    st.caption(
        f"{selected_analysis.get('report', '')}  •  "
        f"Submitted {selected_analysis['submitted'].strftime('%d %b %Y, %I:%M %p')}"
    )


# ---------------------------------------------------------
# Poll status until done, then render the report once
# ---------------------------------------------------------

_PROGRESS_BY_STATUS = {"pending": 0.1, "validation": 0.4, "processing": 0.7}
_report_cache_key = f"report_cache_{analysis_id}"
_token = session.token()

if _report_cache_key in st.session_state:
    render_report(st.session_state[_report_cache_key])
else:

    @st.fragment(run_every="3s")
    def _poll_status() -> None:
        try:
            status_data = api_client.get_analysis_status(_token, analysis_id)
        except api_client.ApiError as exc:
            st.error(f"Could not check analysis status: {exc.detail}")
            return

        status = status_data["status"]

        if status == "failed":
            st.error(f"Analysis failed: {status_data.get('error_message') or 'Unknown error.'}")
            return

        if status != "done":
            st.info(f"Status: {status.capitalize()}. This page refreshes automatically.")
            st.progress(_PROGRESS_BY_STATUS.get(status, 0.1))
            return

        try:
            report = api_client.get_analysis_report(_token, analysis_id)
        except api_client.ApiError as exc:
            st.error(f"Could not load the report: {exc.detail}")
            return

        # Cache it and force a full rerun so this fragment's run_every loop stops --
        # the next run takes the cached branch above instead of continuing to poll.
        st.session_state[_report_cache_key] = report
        st.rerun()

    _poll_status()
