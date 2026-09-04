"""Frontend services package bootstrap.

Loads repo-root .env for local Streamlit runs so service modules can read
AUTH_API_URL, BACKEND_URL, REDIS_URL, and related settings without manual
shell exports.
"""

from __future__ import annotations
import logging
import os
from pathlib import Path

def _load_repo_dotenv() -> None:
	"""Load repo-root .env into os.environ without overriding existing vars."""
	path = Path(__file__).resolve().parents[2] / ".env"
	if not path.is_file():
		return
	for raw in path.read_text().splitlines():
		line = raw.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		key, _, value = line.partition("=")
		key = key.strip()
		value = value.strip().strip("'").strip('"')
		if key:
			os.environ.setdefault(key, value)


_load_repo_dotenv()

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
