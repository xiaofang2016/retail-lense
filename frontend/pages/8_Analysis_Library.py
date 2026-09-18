"""Analysis Library page."""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from components.style import setup
from services import api_client, session


setup("Analysis Library")

# GET /analyses requires a JWT, so the page can't render anything real without a session.
if not session.signed_in():
    st.warning("Please sign in to view your analyses.")
    countdown_notice = st.empty()
    for sec in range(3, 0, -1):
        countdown_notice.info(f"Redirecting in {sec}...")
        time.sleep(1)
    st.switch_page("pages/4_Account.py")
    st.stop()


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("Analysis Library")

st.write(
    "View your previous analyses, check their status, "
    "and access completed reports."
)


# ---------------------------------------------------------
# Fetch analyses from the backend (GET /analyses, queries UserIndex by user_id)
# ---------------------------------------------------------

_STATUS_DISPLAY = {
    "done": "Completed",
    "failed": "Failed",
    "pending": "Processing",
    "validation": "Processing",
    "processing": "Processing",
}

try:
    fetched = api_client.list_analyses(session.token())["items"]
except api_client.ApiError as exc:
    st.error(f"Could not load your analyses: {exc.detail}")
    fetched = []

analyses = [
    {
        "id": item["analysis_id"],
        "report": item["original_filename"],
        "submitted": datetime.fromisoformat(item["created_at"]),
        "status": _STATUS_DISPLAY.get(item["status"], "Processing"),
    }
    for item in fetched
]

st.session_state["analyses"] = analyses


# ---------------------------------------------------------
# Delete confirmation
# ---------------------------------------------------------

delete_id = st.session_state.get(
    "delete_analysis_id"
)

if delete_id:

    delete_analysis = next(
        (
            item
            for item in st.session_state["analyses"]
            if item["id"] == delete_id
        ),
        None,
    )

    if delete_analysis:

        st.warning(
            f"Are you sure you want to delete "
            f"**{delete_analysis['report']}**?"
        )

        confirm_col1, confirm_col2 = st.columns(2)

        with confirm_col1:

            if st.button(
                "Yes, Delete",
                type="primary",
                use_container_width=True,
            ):
                try:
                    api_client.delete_analysis(session.token(), delete_id)

                    st.session_state.pop(
                        "delete_analysis_id"
                    )

                    st.success(
                        "Analysis deleted successfully."
                    )

                    st.rerun()

                except api_client.ApiError as exc:
                    st.error(f"Could not delete this analysis: {exc.detail}")

        with confirm_col2:

            if st.button(
                "Cancel",
                use_container_width=True,
            ):

                st.session_state.pop(
                    "delete_analysis_id"
                )

                st.rerun()


# ---------------------------------------------------------
# Search and filters
# ---------------------------------------------------------

st.subheader("Find an Analysis")

search_col, status_col, date_col = st.columns(
    [2, 1, 1]
)


with search_col:

    search = st.text_input(
        "File name",
        placeholder="Search by file name...",
    )


with status_col:

    status_filter = st.selectbox(
        "Status",
        [
            "All",
            "Completed",
            "Processing",
            "Failed",
        ],
    )


with date_col:

    date_filter = st.selectbox(
        "Date Submitted",
        [
            "All dates",
            "Today",
            "Last 7 days",
            "Last 30 days",
        ],
    )


search_button = st.button(
    "🔍 Search",
    type="primary",
    use_container_width=True,
)


# ---------------------------------------------------------
# Load analysis data
# ---------------------------------------------------------

df = pd.DataFrame(
    st.session_state["analyses"]
)


# ---------------------------------------------------------
# Apply filters
# ---------------------------------------------------------

filtered_df = df.copy()


if search_button:

    if search:

        filtered_df = filtered_df[
            filtered_df["report"].str.contains(
                search,
                case=False,
                na=False,
            )
        ]


    if status_filter != "All":

        filtered_df = filtered_df[
            filtered_df["status"] == status_filter
        ]


    today = datetime.now().date()


    if date_filter == "Today":

        filtered_df = filtered_df[
            filtered_df["submitted"].dt.date == today
        ]


    elif date_filter == "Last 7 days":

        start_date = datetime.now() - timedelta(
            days=7
        )

        filtered_df = filtered_df[
            filtered_df["submitted"] >= start_date
        ]


    elif date_filter == "Last 30 days":

        start_date = datetime.now() - timedelta(
            days=30
        )

        filtered_df = filtered_df[
            filtered_df["submitted"] >= start_date
        ]


# ---------------------------------------------------------
# Analysis list
# ---------------------------------------------------------

st.divider()

st.subheader("Your Analyses")


if filtered_df.empty:

    st.info(
        "No analyses match your search or selected filters."
    )

else:

    # -----------------------------------------------------
    # Table header
    # -----------------------------------------------------

    (
        header_col1,
        header_col2,
        header_col3,
        header_col4,
        header_col5,
    ) = st.columns(
        [3, 2, 1.5, 1, 0.8]
    )


    with header_col1:
        st.markdown("**Report**")


    with header_col2:
        st.markdown("**Date Submitted**")


    with header_col3:
        st.markdown("**Status**")


    with header_col4:
        st.markdown("**Action**")


    with header_col5:
        st.markdown("**Delete**")


    # -----------------------------------------------------
    # Analysis rows
    # -----------------------------------------------------

    for _, analysis in filtered_df.iterrows():

        (
            col1,
            col2,
            col3,
            col4,
            col5,
        ) = st.columns(
            [3, 2, 1.5, 1, 0.8]
        )


        status = analysis["status"]


        # -------------------------------------------------
        # Report name
        # -------------------------------------------------

        with col1:

            if status == "Completed":

                if st.button(
                    analysis["report"],
                    key=f"report_{analysis['id']}",
                    type="tertiary",
                ):

                    st.session_state[
                        "selected_analysis"
                    ] = {
                        "id": analysis["id"],
                        "report": analysis["report"],
                        "submitted": analysis["submitted"],
                        "status": analysis["status"],
                    }

                    st.switch_page(
                        "pages/9_Analysis_Report.py"
                    )

            else:

                st.write(
                    analysis["report"]
                )


        # -------------------------------------------------
        # Date submitted
        # -------------------------------------------------

        with col2:

            st.write(
                analysis["submitted"].strftime(
                    "%d %b %Y, %I:%M %p"
                )
            )


        # -------------------------------------------------
        # Status
        # -------------------------------------------------

        with col3:

            if status == "Completed":

                st.success(
                    "Completed",
                    icon="✅",
                )

            elif status == "Processing":

                st.info(
                    "Processing",
                    icon="⏳",
                )

            elif status == "Failed":

                st.error(
                    "Failed",
                    icon="❌",
                )


        # -------------------------------------------------
        # View report
        # -------------------------------------------------

        # with col4:

        #     if status == "Completed":

        #         if st.button(
        #             "View",
        #             key=f"view_{analysis['id']}",
        #             use_container_width=True,
        #         ):

        #             st.session_state[
        #                 "selected_analysis"
        #             ] = {
        #                 "id": analysis["id"],
        #                 "report": analysis["report"],
        #                 "submitted": analysis["submitted"],
        #                 "status": analysis["status"],
        #             }

        #             st.switch_page(
        #                 "pages/9_Analysis_Report.py"
        #             )     

        # -------------------------------------------------
        # View report
        # -------------------------------------------------

        with col4:

            if status == "Completed":

                if st.button(
                    "View",
                    key=f"view_{analysis['id']}",
                    use_container_width=True,
                ):

                    st.session_state["selected_analysis"] = {
                        "id": analysis["id"],
                        "report": analysis["report"],
                        "submitted": analysis["submitted"],
                        "status": analysis["status"],
                    }

                    # Store analysis ID in URL so the report
                    # can be restored after browser refresh.
                    st.query_params["analysis_id"] = str(
                        analysis["id"]
                    )

                    st.switch_page(
                        "pages/9_Analysis_Report.py"
                    )               


        # -------------------------------------------------
        # Delete
        # -------------------------------------------------

        with col5:

            if st.button(
                "🗑️",
                key=f"delete_{analysis['id']}",
                help="Delete this analysis",
                use_container_width=True,
            ):

                st.session_state[
                    "delete_analysis_id"
                ] = analysis["id"]

                st.rerun()


        st.divider()


# ---------------------------------------------------------
# Upload new data
# ---------------------------------------------------------

if st.button(
    "📤 Upload New Data",
    use_container_width=True,
):

    st.switch_page(
        "pages/6_Upload.py"
    )