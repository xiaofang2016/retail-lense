"""Read and cache runtime secrets from AWS Secrets Manager."""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache


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
        for key in ("JWT_SECRET", "jwt_secret", "secret"):
            candidate = payload.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        raise RuntimeError("Secret JSON must contain JWT_SECRET, jwt_secret, or secret")

    if not value:
        raise RuntimeError("Secret value is empty")
    return value


@lru_cache(maxsize=16)
def get_secret(secret_name: str) -> str:
    """Retrieve one secret once per process or warm Lambda environment."""
    if not secret_name:
        raise ValueError("secret_name is required")

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
