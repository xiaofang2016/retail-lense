"""Unsupervised K-Means segmentation on RFM features."""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Ordered best -> worst. Default k is 4; fewer unique customers use fewer labels.
_SEGMENT_LABELS = ["High Value", "Loyal", "At Risk", "Lost"]


def fit_segments(rfm_frame: pd.DataFrame, k: int = 4) -> pd.DataFrame:
    features = rfm_frame[["Recency", "Frequency", "Monetary"]]
    n_samples = len(features)
    if n_samples == 0:
        raise ValueError("RFM frame is empty; need at least one customer to cluster")
    k = max(1, min(int(k), n_samples))
    scaled = StandardScaler().fit_transform(features)

    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    rfm_frame = rfm_frame.copy()
    rfm_frame["Cluster"] = model.fit_predict(scaled)

    cluster_means = rfm_frame.groupby("Cluster")[["Recency", "Frequency", "Monetary"]].mean()

    # Rank each cluster on each metric (0 = worst). Low recency is good, so its rank is inverted.
    recency_rank = cluster_means["Recency"].rank(ascending=False) - 1
    frequency_rank = cluster_means["Frequency"].rank(ascending=True) - 1
    monetary_rank = cluster_means["Monetary"].rank(ascending=True) - 1
    score = recency_rank + frequency_rank + monetary_rank

    ordered_clusters = score.sort_values(ascending=False).index.tolist()
    label_by_cluster = {
        cluster: _SEGMENT_LABELS[i] if i < len(_SEGMENT_LABELS) else f"Segment {i + 1}"
        for i, cluster in enumerate(ordered_clusters)
    }

    rfm_frame["Segment"] = rfm_frame["Cluster"].map(label_by_cluster)
    return rfm_frame.drop(columns=["Cluster"])
