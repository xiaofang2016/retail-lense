"""Recency, Frequency, Monetary aggregation per CustomerID."""

import pandas as pd


def compute_rfm(frame: pd.DataFrame) -> pd.DataFrame:
    reference_date = frame["InvoiceDate"].max() + pd.Timedelta(days=1)

    rfm = frame.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda dates: (reference_date - dates.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("TotalPrice", "sum"),
    )
    return rfm.reset_index()
