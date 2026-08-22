"""Read secrets at runtime via the EC2 instance role. Do not use SSM Parameter Store."""

from __future__ import annotations

import os


def get_secret(secret_name: str) -> str:
    # TODO: secretsmanager GetSecretValue
    _ = secret_name
    return os.getenv("JWT_SECRET", "")
