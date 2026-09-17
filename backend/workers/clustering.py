"""EC2 worker: RFM + K-Means on a validated upload. Long-running process on the instance.

This is the single consolidated worker for the whole pipeline (per docker-compose's
`python -m workers.clustering`): it polls SQS, and for each S3 PUT notification on
uploads/ it validates, cleans, engineers RFM features, clusters, builds figures, calls
the LLM for advice, and writes results/ to S3. It does NOT set status="done" -- that is
the S3-triggered completion Lambda's job once report.json lands.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote_plus

import numpy as np
import pandas as pd

from core.settings import get_settings
from ml import cleaning, clustering, figures, insights, preprocess, rfm
from services import s3, sqs
from services.analysis_store import get_analysis_store
from workers import advice_generate, validate_upload

logger = logging.getLogger("workers.clustering")


class _NumpyJSONEncoder(json.JSONEncoder):
    """Plotly figures (ml/figures.py) and pandas frames can carry numpy types that
    the stdlib json module doesn't know how to serialize on its own."""

    def default(self, o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, (pd.Timestamp, dt.date, dt.datetime)):
            # numpy datetime64 arrays convert to plain datetime.datetime via .tolist(),
            # not pd.Timestamp, so both need to be handled here.
            return o.isoformat()
        return super().default(o)


def _parse_upload_key(key: str) -> tuple[str, str, str]:
    """uploads/{user_id}/{analysis_id}/raw.(csv|xlsx) -> (user_id, analysis_id, filename)."""
    settings = get_settings()
    relative = key.removeprefix(settings.s3_prefix_uploads)
    user_id, analysis_id, filename = relative.split("/", 2)
    return user_id, analysis_id, filename


def _s3_events(message_body: dict[str, Any]) -> list[tuple[str, str]]:
    """Parse an S3 bucket-notification message body into a list of (bucket, key)."""
    events: list[tuple[str, str]] = []
    for record in message_body.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        events.append((bucket, key))
    return events


def _read_frame(body: bytes, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(body))
    return pd.read_csv(io.BytesIO(body))


def process_upload(bucket: str, key: str) -> None:
    _ = bucket
    settings = get_settings()
    store = get_analysis_store()
    user_id, analysis_id, filename = _parse_upload_key(key)

    store.update(analysis_id, status="validation")

    body = s3.get_object_bytes(key)

    try:
        validate_upload.validate(body, filename)
    except ValueError as exc:
        store.update(analysis_id, status="failed", error_message=str(exc))
        return

    store.update(analysis_id, status="processing")

    try:
        frame = _read_frame(body, filename)
        frame = cleaning.clean(frame)
        frame = preprocess.preprocess(frame)

        rfm_frame = rfm.compute_rfm(frame)
        rfm_frame = clustering.fit_segments(rfm_frame, k=settings.analysis_k)

        report_figures = figures.build_all(frame, rfm_frame)
        report_insights = insights.summarise(frame, rfm_frame)
        # advice = advice_generate.generate(report_insights)
        try:
            advice = advice_generate.generate(report_insights)
        except Exception:  # Arya
            logger.exception("analysis %s: advice generation failed, continuing without it", analysis_id)
            advice = ""

        report = {
            "metrics": report_insights,
            "figures": report_figures,
            "segments": rfm_frame.to_dict(orient="records"),
            "advice": advice,
        }
        metadata = {
            "analysis_id": analysis_id,
            "user_id": user_id,
            "row_count": int(len(frame)),
            "generated_at": datetime.now(UTC).isoformat(),
        }

        s3.put_result(
            user_id, analysis_id, "report.json", json.dumps(report, cls=_NumpyJSONEncoder).encode("utf-8")
        )
        s3.put_result(
            user_id, analysis_id, "metadata.json", json.dumps(metadata, cls=_NumpyJSONEncoder).encode("utf-8")
        )
    except Exception as exc:  # noqa: BLE001 -- any pipeline failure must flip status to failed
        logger.exception("analysis %s failed during processing", analysis_id)
        store.update(analysis_id, status="failed", error_message=str(exc))


def run() -> None:
    while True:
        jobs = sqs.receive_jobs(max_messages=1, wait_time_seconds=20)
        for job in jobs:
            for bucket, key in _s3_events(job["body"]):
                try:
                    process_upload(bucket, key)
                except Exception:  # noqa: BLE001 -- keep polling even if one job is malformed
                    logger.exception("unhandled error processing s3://%s/%s", bucket, key)
            sqs.delete_job(job["receipt_handle"])


if __name__ == "__main__":
    run()
