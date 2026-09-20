"""Read and cache runtime secrets from AWS Secrets Manager."""

from __future__ import annotations

import base64
import json
import os
from functools import lru_cache

from core.settings import get_settings


def _local_fallback(secret_name: str) -> str:
    """Local/test dev only: no real Secrets Manager call, read the .env fallback instead."""
    if secret_name.endswith("/SMTP_USER"):
        return os.getenv("SMTP_USER", "")
    if secret_name.endswith("/SMTP_PASSWORD"):
        return os.getenv("SMTP_PASSWORD", "")
    settings = get_settings()
    if secret_name == settings.openai_secret_name:
        return os.getenv("OPENAI_API_KEY", "")
    return os.getenv("JWT_SECRET", "")


def _secrets_client():
    from core.aws import client as aws_client

    return aws_client("secretsmanager")


def _extract_secret_value(value: str, field: str | None = None) -> str:
    """Accept a plain secret string or a JSON object."""
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        keys = []
        if field:
            keys.append(field)
        keys.extend(("JWT_SECRET", "jwt_secret", "OPENAI_API_KEY", "openai_api_key", "secret"))
        for key in keys:
            candidate = payload.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        raise RuntimeError(
            "Secret JSON must contain JWT_SECRET, OPENAI_API_KEY, jwt_secret, "
            "openai_api_key, secret"
            + (f", or {field}" if field else "")
        )

    if not value:
        raise RuntimeError("Secret value is empty")
    return value


@lru_cache(maxsize=16)
def get_secret(secret_name: str, field: str | None = None) -> str:
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
    return _extract_secret_value(value, field=field)
