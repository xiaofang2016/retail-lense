"""Build Plotly figures for the report and serialize them to JSON-safe dicts."""

import pandas as pd
import plotly.express as px


def sales_over_time(frame: pd.DataFrame) -> dict:
    daily = frame.set_index("InvoiceDate").resample("D")["Quantity"].sum().reset_index()
    fig = px.line(daily, x="InvoiceDate", y="Quantity", markers=True, title="Daily Units Sold")
    fig.update_layout(xaxis_title="Date", yaxis_title="Units Sold", hovermode="x unified")
    return fig.to_dict()


def top_products(frame: pd.DataFrame, n: int = 8) -> dict:
    grouped = (
        frame.groupby("Description")
        .agg(Revenue=("TotalPrice", "sum"), Quantity=("Quantity", "sum"))
        .sort_values("Revenue", ascending=False)
        .head(n)
        .reset_index()
    )
    fig = px.bar(
        grouped,
        x="Revenue",
        y="Description",
        orientation="h",
        text="Revenue",
        title=f"Top {n} Products by Revenue",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Revenue", yaxis_title="Product")
    return fig.to_dict()


def revenue_over_time(frame: pd.DataFrame) -> dict:
    monthly = frame.set_index("InvoiceDate").resample("ME")["TotalPrice"].sum().reset_index()
    fig = px.area(monthly, x="InvoiceDate", y="TotalPrice", markers=True, title="Monthly Revenue")
    fig.update_layout(xaxis_title="Month", yaxis_title="Revenue", hovermode="x unified")
    return fig.to_dict()


def segment_distribution(rfm_frame: pd.DataFrame) -> dict:
    counts = rfm_frame.groupby("Segment").size().reset_index(name="Customers")
    fig = px.bar(
        counts,
        x="Segment",
        y="Customers",
        text="Customers",
        title="Customer Distribution by Segment",
    )
    fig.update_layout(xaxis_title="Segment", yaxis_title="Customers")
    return fig.to_dict()


def build_all(frame: pd.DataFrame, rfm_frame: pd.DataFrame) -> dict[str, dict]:
    return {
        "sales_over_time": sales_over_time(frame),
        "top_products": top_products(frame),
        "revenue_over_time": revenue_over_time(frame),
        "segment_distribution": segment_distribution(rfm_frame),
    }
