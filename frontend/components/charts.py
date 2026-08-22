"""Segmentation / RFM charts for gallery and private reports."""


def render_segment_charts(segments=None) -> None:
    import streamlit as st

    if not segments:
        st.write("Charts will appear here once analysis results are available.")
        return
    # TODO: plotly/altair charts for RFM distributions and cluster sizes
    st.write(segments)
