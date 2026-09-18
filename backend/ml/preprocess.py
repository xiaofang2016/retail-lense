"""Parse dates, scale RFM inputs, train/holdout split if needed."""

import pandas as pd


def preprocess(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["InvoiceDate"] = pd.to_datetime(frame["InvoiceDate"])
    frame["TotalPrice"] = frame["Quantity"] * frame["UnitPrice"]
    return frame
