"""Missing values, outliers, cancelled invoices, non-positive quantities."""

import pandas as pd


def _clip_outliers_iqr(series: pd.Series) -> pd.Series:
    """Clip (not drop) values outside 1.5*IQR so legitimate bulk orders survive."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return series.clip(lower=max(lower, 0), upper=upper)


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.dropna(subset=["CustomerID"]).copy()
    frame["CustomerID"] = frame["CustomerID"].astype(str).str.strip()

    # Cancelled orders carry an InvoiceNo prefixed with "C" in the UCI retail format.
    frame = frame[~frame["InvoiceNo"].astype(str).str.startswith("C")]

    # Negative Quantity = returns/adjustments, not real sales -- drop them.
    frame = frame[frame["Quantity"] > 0]

    # Zero UnitPrice = free/promotional line items with no monetary value for RFM -- drop them.
    frame = frame[frame["UnitPrice"] > 0]

    frame["Quantity"] = _clip_outliers_iqr(frame["Quantity"])
    frame["UnitPrice"] = _clip_outliers_iqr(frame["UnitPrice"])

    return frame.reset_index(drop=True)
