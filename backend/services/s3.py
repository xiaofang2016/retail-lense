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


def upload_key(user_id: str, analysis_id: str, file_extension: str) -> str:
    """uploads/{user_id}/{analysis_id}/raw.(csv|xlsx) -- the fixed key the client PUTs to."""
    settings = get_settings()
    return f"{settings.s3_prefix_uploads}{user_id}/{analysis_id}/raw.{file_extension}"


def presign_put_url(key: str, content_type: str, expires_in: int = 900) -> str:
    """Presigned S3 PUT URL scoped to one key, used by POST /analyses."""
    settings = get_settings()
    return s3_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in,
    )


def put_result(user_id: str, analysis_id: str, filename: str, body: bytes) -> str:
    """Write results/{user_id}/{analysis_id}/{filename} (report.json / metadata.json)."""
    settings = get_settings()
    key = f"{settings.s3_prefix_results}{user_id}/{analysis_id}/{filename}"
    s3_client().put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    return key


def get_object_json(key: str) -> dict:
    """Read and parse a JSON object (report.json / metadata.json)."""
    import json

    return json.loads(get_object_bytes(key))
