"""Reusable template for rendering a completed analysis report.

Takes the parsed report.json (as returned by GET /analyses/{id}/report) and renders it.
Used by pages/9_Analysis_Report.py, and reusable wherever a report needs to be displayed
from the Analysis Library.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _render_figure(spec: dict | None, empty_message: str) -> None:
    if not spec:
        st.info(empty_message)
        return
    fig = go.Figure(data=spec.get("data"), layout=spec.get("layout"))
    st.plotly_chart(fig, use_container_width=True)


def render_report(report: dict[str, Any]) -> None:
    metrics = report.get("metrics", {})
    figs = report.get("figures", {})
    segments = pd.DataFrame(report.get("segments", []))
    advice = report.get("advice") or ""

    # -----------------------------------------------------
    # Business Overview
    # -----------------------------------------------------

    st.subheader("Business Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Customers", f"{metrics.get('total_customers', 0):,}")

    with col2:
        st.metric("Total Invoices", f"{metrics.get('total_invoices', 0):,}")

    with col3:
        st.metric("Total Revenue", f"${metrics.get('total_revenue', 0):,.2f}")

    with col4:
        st.metric("Average Order Value", f"${metrics.get('average_order_value', 0):,.2f}")

    # -----------------------------------------------------
    # Sales Over Time
    # -----------------------------------------------------

    st.divider()
    st.subheader("1. Sales Over Time")
    _render_figure(figs.get("sales_over_time"), "Sales-over-time chart is not available.")

    # -----------------------------------------------------
    # Top Products
    # -----------------------------------------------------

    st.divider()
    st.subheader("2. Top Products")
    _render_figure(figs.get("top_products"), "Top-products chart is not available.")

    # -----------------------------------------------------
    # Revenue Over Time
    # -----------------------------------------------------

    st.divider()
    st.subheader("3. Revenue Over Time")
    _render_figure(figs.get("revenue_over_time"), "Revenue-over-time chart is not available.")

    # -----------------------------------------------------
    # RFM Analysis
    # -----------------------------------------------------

    st.divider()
    st.subheader("4. RFM Analysis")

    st.write("RFM analysis evaluates customers based on Recency, Frequency and Monetary value.")

    if not segments.empty:
        rfm_col1, rfm_col2, rfm_col3 = st.columns(3)

        with rfm_col1:
            st.metric("Average Recency", f"{segments['Recency'].mean():.0f} days")

        with rfm_col2:
            st.metric("Average Frequency", f"{segments['Frequency'].mean():.1f} orders")

        with rfm_col3:
            st.metric("Average Monetary Value", f"${segments['Monetary'].mean():,.2f}")

    _render_figure(figs.get("segment_distribution"), "Segment-distribution chart is not available.")

    # -----------------------------------------------------
    # Customer Segmentation
    # -----------------------------------------------------

    st.divider()
    st.subheader("5. Customer Segmentation")

    st.write("Explore customer segments identified through RFM analysis and K-Means clustering.")

    if segments.empty:
        st.info("No customer-level segmentation data is available for this report.")
    else:
        segment_options = ["All Customers"] + sorted(segments["Segment"].unique().tolist())
        selected_segment = st.selectbox("Explore segment", segment_options)

        if selected_segment == "All Customers":
            selected_data = segments
        else:
            selected_data = segments[segments["Segment"] == selected_segment]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Customers", f"{len(selected_data):,}")

        with col2:
            st.metric("Avg. Recency", f"{selected_data['Recency'].mean():.0f} days")

        with col3:
            st.metric("Avg. Frequency", f"{selected_data['Frequency'].mean():.1f}")

        with col4:
            st.metric("Avg. Monetary", f"${selected_data['Monetary'].mean():,.2f}")

        csv_data = selected_data.to_csv(index=False).encode("utf-8")
        file_name = selected_segment.lower().replace(" ", "_").replace("-", "_")

        st.download_button(
            label="📥 Download Customer Details",
            data=csv_data,
            file_name=f"{file_name}_customer_details.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download the detailed customer list for the selected segment.",
        )

    # -----------------------------------------------------
    # Business Decisions
    # -----------------------------------------------------

    st.divider()
    st.subheader("6. Business Decisions & Recommendations")

    if advice:
        st.markdown(advice)
    else:
        st.info("No LLM-generated recommendations are available for this report.")
