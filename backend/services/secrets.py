"""Read and cache runtime secrets from AWS Secrets Manager."""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache

from core.settings import get_settings


def secrets_client():
    import boto3

    settings = get_settings()
    if settings.aws_profile:
        return boto3.Session(
            profile_name=settings.aws_profile,
            region_name=settings.aws_region,
        ).client("secretsmanager")
    return boto3.client("secretsmanager", region_name=settings.aws_region)


def _local_fallback(secret_name: str) -> str:
    """Local/test dev only: no real Secrets Manager call, read the .env fallback instead."""
    settings = get_settings()
    if secret_name == settings.openai_secret_name:
        return os.getenv("OPENAI_API_KEY", "")
    return os.getenv("JWT_SECRET", "")


def _secrets_client():
    import boto3

    region = os.getenv("AWS_REGION", "us-east-1")
    profile = os.getenv("AWS_PROFILE", "").strip()
    if profile and not os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return boto3.Session(profile_name=profile, region_name=region).client("secretsmanager")
    return boto3.client("secretsmanager", region_name=region)


def _extract_secret_value(value: str) -> str:
    """Accept a plain secret string or a JSON object containing the JWT key."""
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        for key in ("JWT_SECRET", "jwt_secret", "OPENAI_API_KEY", "openai_api_key", "secret"):
            candidate = payload.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        raise RuntimeError("Secret JSON must contain JWT_SECRET, OPENAI_API_KEY, jwt_secret, openai_api_key, or secret")

    if not value:
        raise RuntimeError("Secret value is empty")
    return value


@lru_cache(maxsize=16)
def get_secret(secret_name: str) -> str:
    """Retrieve one secret once per process or warm Lambda environment."""
    if not secret_name:
        raise ValueError("secret_name is required")

   
    if os.getenv("APP_ENV", "local") != "aws":
        return _local_fallback(secret_name)

    response = _secrets_client().get_secret_value(SecretId=secret_name)
    if "SecretString" in response:
        value = response["SecretString"]
    else:
        binary = response["SecretBinary"]
        value = (
            binary.decode("utf-8")
            if isinstance(binary, bytes)
            else base64.b64decode(binary).decode("utf-8")
        )
    return _extract_secret_value(value)
