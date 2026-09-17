"""Numeric summaries fed to the LLM prompt (unique customers, AOV, segment sizes)."""

import pandas as pd


def summarise(frame: pd.DataFrame, rfm_frame: pd.DataFrame) -> dict:
    total_customers = int(rfm_frame.shape[0])
    total_invoices = int(frame["InvoiceNo"].nunique())
    total_revenue = float(frame["TotalPrice"].sum())
    average_order_value = total_revenue / total_invoices if total_invoices else 0.0

    segments = []
    for segment, group in rfm_frame.groupby("Segment"):
        segments.append(
            {
                "segment": segment,
                "customers": int(len(group)),
                "avg_recency": float(group["Recency"].mean()),
                "avg_frequency": float(group["Frequency"].mean()),
                "avg_monetary": float(group["Monetary"].mean()),
            }
        )

    return {
        "total_customers": total_customers,
        "total_invoices": total_invoices,
        "total_revenue": total_revenue,
        "average_order_value": average_order_value,
        "segments": segments,
    }
