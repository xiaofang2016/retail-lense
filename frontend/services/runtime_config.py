"""Load production frontend secrets from Secrets Manager.

Secret id is `retaillen/<ENV_VAR>`:
  retaillen/AUTH_API_URL
  retaillen/REDIS_URL
  retaillen/REDIS_PASSWORD
  retaillen/SESSION_COOKIE_PASSWORD

When APP_ENV=aws, empty values are fetched from those secrets (instance role).
Local/test keep the .env values and never call Secrets Manager.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from functools import lru_cache

SECRET_KEYS = ("AUTH_API_URL", "REDIS_URL", "REDIS_PASSWORD", "SESSION_COOKIE_PASSWORD")
SECRET_PREFIX = "retaillen/"


def secret_id(env_key: str) -> str:
    return f"{SECRET_PREFIX}{env_key}"


def _app_env() -> str:
    return (os.getenv("APP_ENV") or "local").strip()


def should_fetch(env_key: str) -> bool:
    if _app_env() != "aws":
        return False
    return not (os.getenv(env_key) or "").strip()


def keys_to_fetch() -> tuple[str, ...]:
    return tuple(key for key in SECRET_KEYS if should_fetch(key))


def _extract_value(raw: str, field: str, name: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        value = raw.strip()
        if not value:
            raise RuntimeError(f"Secret {name} is empty")
        return value
    if isinstance(payload, dict):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise RuntimeError(f"Secret {name} JSON is missing {field}")
    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    raise RuntimeError(f"Secret {name} must be a string or JSON object")


@lru_cache(maxsize=8)
def _get_secret_string(name: str) -> str:
    import boto3

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    client = boto3.Session(region_name=region).client("secretsmanager")
    response = client.get_secret_value(SecretId=name)
    if "SecretString" not in response:
        raise RuntimeError(f"Secret {name} has no SecretString")
    return response["SecretString"]


@lru_cache(maxsize=1)
def apply() -> dict[str, str]:
    loaded: dict[str, str] = {}
    for env_key in keys_to_fetch():
        name = secret_id(env_key)
        value = _extract_value(_get_secret_string(name), env_key, name)
        if env_key == "AUTH_API_URL":
            value = value.rstrip("/")
        os.environ[env_key] = value
        loaded[env_key] = value
    return loaded


def export_shell() -> str:
    apply()
    lines = []
    for key in SECRET_KEYS:
        value = os.getenv(key, "")
        if value:
            lines.append(f"export {key}={shlex.quote(value)}")
    return "\n".join(lines)


if __name__ == "__main__":
    if "--export" in sys.argv:
        print(export_shell())
    else:
        loaded = apply()
        if not loaded:
            print("using .env values (Secrets Manager not needed)", file=sys.stderr)
        else:
            print("loaded from Secrets Manager: " + ", ".join(sorted(loaded)), file=sys.stderr)
