import pandas as pd

from ml.clustering import fit_segments


def test_fit_segments_clamps_k_when_one_customer():
    frame = pd.DataFrame(
        {
            "CustomerID": [1],
            "Recency": [10],
            "Frequency": [2],
            "Monetary": [50.0],
        }
    )
    result = fit_segments(frame, k=4)
    assert len(result) == 1
    assert result.iloc[0]["Segment"] == "High Value"


def test_fit_segments_uses_requested_k_when_enough_customers():
    frame = pd.DataFrame(
        {
            "CustomerID": [1, 2, 3, 4],
            "Recency": [5, 20, 40, 80],
            "Frequency": [10, 6, 3, 1],
            "Monetary": [400.0, 200.0, 80.0, 20.0],
        }
    )
    result = fit_segments(frame, k=4)
    assert set(result["Segment"]) <= {"High Value", "Loyal", "At Risk", "Lost"}
    assert result["Segment"].nunique() == 4
