"""Frontend services package bootstrap.

Loads a small allowlist from repo-root .env for local Streamlit runs.
AWS_PROFILE and access keys are never copied into this process.
On APP_ENV=aws, empty AUTH_API_URL / REDIS_URL / REDIS_PASSWORD /
SESSION_COOKIE_PASSWORD are read from Secrets Manager as retaillen/<NAME>.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path

_FRONTEND_ENV_KEYS = {
    "APP_ENV",
    "APP_LOG_LEVEL",
    "AUTH_API_URL",
    "BACKEND_URL",
    "FRONTEND_PORT",
    "REDIS_PASSWORD",
    "REDIS_URL",
    "REMEMBER_ME_DAYS",
    "SESSION_COOKIE_PASSWORD",
    "TOKEN_TIME",
}


def _load_repo_dotenv() -> None:
    """Load frontend settings from repo-root .env without overriding existing vars."""
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("AWS_") or key not in _FRONTEND_ENV_KEYS:
            continue
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


_load_repo_dotenv()

from .runtime_config import apply as _apply_frontend_secrets

_apply_frontend_secrets()


def _configure_logging() -> None:
    level_name = (os.getenv("APP_LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)

_configure_logging()
