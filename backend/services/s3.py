"""S3 helpers. Prefixes: public/, uploads/{user_id}/, results/{user_id}/."""

from __future__ import annotations

import os

BUCKET = os.getenv("S3_BUCKET", "retaillen-dev")


def put_upload(user_id: str, key: str, body: bytes, content_type: str) -> str:
    # TODO: put_object uploads/{user_id}/{key}
    _ = (user_id, key, body, content_type)
    return f"s3://{BUCKET}/uploads/{user_id}/{key}"


def put_result(user_id: str, analysis_id: str, body: bytes) -> str:
    # TODO: put_object results/{user_id}/{analysis_id}
    _ = (user_id, analysis_id, body)
    return f"s3://{BUCKET}/results/{user_id}/{analysis_id}"
