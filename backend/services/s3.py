"""S3 helpers. Prefixes: public/, uploads/{user_id}/, results/{user_id}/."""

from __future__ import annotations

import logging
from pathlib import Path
from core.settings import get_settings

logger = logging.getLogger("s3")

_LOCAL_SAMPLE_CANDIDATES = (
    Path(__file__).resolve().parents[1] / "data" / "samples" / "transactions_sample.csv",
    Path(__file__).resolve().parents[2] / "data" / "samples" / "transactions_sample.csv",
)


def s3_client():
    import boto3

    settings = get_settings()
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        ).client("s3")
    return boto3.client("s3", region_name=settings.aws_region)


def get_object_bytes(key: str) -> bytes:
    settings = get_settings()
    response = s3_client().get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()


def get_transactions_sample() -> tuple[bytes, str]:
    """Return (csv_bytes, source). source is 's3' or 'local'."""
    settings = get_settings()
    s3_error: str | None = None
    if settings.app_env != "test":
        try:
            body = get_object_bytes(settings.s3_transactions_sample_key)
            return body, "s3"
        except Exception as exc:
            s3_error = (
                f"s3://{settings.s3_bucket}/{settings.s3_transactions_sample_key} "
                f"(APP_ENV={settings.app_env}, profile={settings.aws_profile or 'default/instance-role'}): {exc}"
            )
            logger.warning("s3 sample failed: %s", s3_error)
    for sample_path in _LOCAL_SAMPLE_CANDIDATES:
        if sample_path.is_file():
            return sample_path.read_bytes(), "local"
    if s3_error:
        raise FileNotFoundError(f"{s3_error}. No local copy exists")
    raise FileNotFoundError(
        "transactions_sample.csv was not read from S3 "
        f"(APP_ENV={settings.app_env}) and no local copy exists"
    )


def put_upload(user_id: str, key: str, body: bytes, content_type: str) -> str:
    # TODO: put_object uploads/{user_id}/{key}
    settings = get_settings()
    _ = (user_id, key, body, content_type)
    return f"s3://{settings.s3_bucket}/uploads/{user_id}/{key}"


def put_result(user_id: str, analysis_id: str, body: bytes) -> str:
    # TODO: put_object results/{user_id}/{analysis_id}
    settings = get_settings()
    _ = (user_id, analysis_id, body)
    return f"s3://{settings.s3_bucket}/results/{user_id}/{analysis_id}"
