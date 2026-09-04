"""FastAPI app hosted on EC2 behind the ALB. Sign-in can run on Lambda; other routes stay here."""

import logging
import os
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from api.routers import analyses, auth, reports, uploads, users
from core.security.request_ip import client_ip
from core.settings import get_settings

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

app = FastAPI(title="Retail Lense API", version="0.1.0")

logger = logging.getLogger("retaillen.backend.http")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
_configure_logging()

@app.middleware("http")
async def log_http_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("x-request-id") or uuid4().hex[:12]
    method = request.method
    path = request.url.path
    source_ip = client_ip(request)
    started = time.monotonic()
    logger.info(
        "request_id=%s method=%s path=%s source_ip=%s event=request_started",
        request_id,
        method,
        path,
        source_ip,
    )
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.error(
            "request_id=%s method=%s path=%s source_ip=%s duration_ms=%s error_type=%s "
            "event=request_failed",
            request_id,
            method,
            path,
            source_ip,
            elapsed_ms,
            type(exc).__name__,
        )
        raise

    elapsed_ms = round((time.monotonic() - started) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s source_ip=%s status=%s duration_ms=%s "
        "event=request_finished",
        request_id,
        method,
        path,
        source_ip,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
app.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    payload = {
        "status": "ok",
        "store": "dynamodb" if settings.uses_dynamodb() else "memory",
    }
    if settings.ddb_endpoint:
        payload["ddb_endpoint"] = settings.ddb_endpoint
    return payload
