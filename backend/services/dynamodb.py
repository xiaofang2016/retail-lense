"""DynamoDB access. Tables: Users, LoginHistory, PasswordReset, Otps. No SQL / RDS.

Analyses table access lives in services/analysis_store.py, not here.
"""

from __future__ import annotations

import os
from typing import Any

from core.settings import get_settings

USERS_TABLE = os.getenv("DDB_USERS_TABLE", "retaillen-users")
LOGIN_HISTORY_TABLE = os.getenv("DDB_LOGIN_HISTORY_TABLE", "retaillen-login-history")
PASSWORD_RESET_TABLE = os.getenv("DDB_PASSWORD_RESET_TABLE", "retaillen-password-reset")
OTPS_TABLE = os.getenv("DDB_OTPS_TABLE", "retaillen-otps")


def dynamodb_resource():
    """boto3 DynamoDB resource. Uses DDB_ENDPOINT when set (DynamoDB Local)."""
    import boto3

    settings = get_settings()
    kwargs: dict[str, str] = {"region_name": settings.aws_region}
    if settings.ddb_endpoint:
        kwargs["endpoint_url"] = settings.ddb_endpoint
        kwargs["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID") or "local"
        kwargs["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY") or "local"
        return boto3.resource("dynamodb", **kwargs)
    # Lambda uses the function execution role. Never load a laptop AWS_PROFILE.
    if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return boto3.resource("dynamodb", **kwargs)
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        ).resource("dynamodb")
    return boto3.resource("dynamodb", **kwargs)


def get_user(email: str) -> dict[str, Any] | None:
    # TODO: GetItem on Users (pk = email)
    _ = email
    return None


def put_user(item: dict[str, Any]) -> None:
    # TODO: PutItem Users
    _ = item


def put_otp(email: str, code: str, ttl: int) -> None:
    # TODO: PutItem Otps with TTL attribute
    _ = (email, code, ttl)
