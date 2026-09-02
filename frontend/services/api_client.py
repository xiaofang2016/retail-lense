"""HTTP client for the FastAPI backend. JWT stays in Streamlit session_state."""

from __future__ import annotations

import logging
import os
import time
from typing import Any
from uuid import uuid4

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# Base Function URL for both /auth/signin and /auth/register. Empty = FastAPI.
AUTH_API_URL = os.getenv("AUTH_API_URL", "").strip().rstrip("/")

logger = logging.getLogger("retaillen.frontend.http")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail", response.text)
        if isinstance(detail, list):
            parts = []
            for item in detail:
                if isinstance(item, dict):
                    parts.append(str(item.get("msg", item)))
                else:
                    parts.append(str(item))
            return "; ".join(parts)
        return str(detail)
    except Exception:
        return response.text or f"HTTP {response.status_code}"


def _client(token: str | None = None) -> httpx.Client:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=BACKEND_URL, timeout=30.0, headers=headers)


def _send(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    request_id = uuid4().hex[:12]
    request = client.build_request(method, url, **kwargs)
    request.headers["x-request-id"] = request_id
    safe_url = str(request.url).split("?", 1)[0]
    started = time.monotonic()
    logger.info("request_id=%s method=%s url=%s event=request_started", request_id, method.upper(), safe_url)
    try:
        response = client.send(request)
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.error(
            "request_id=%s method=%s url=%s duration_ms=%s error_type=%s event=request_failed",
            request_id,
            method.upper(),
            safe_url,
            elapsed_ms,
            type(exc).__name__,
        )
        raise
    elapsed_ms = round((time.monotonic() - started) * 1000)
    logger.info(
        "request_id=%s method=%s url=%s status=%s duration_ms=%s event=request_finished",
        request_id,
        method.upper(),
        safe_url,
        response.status_code,
        elapsed_ms,
    )
    return response


def _request(method: str, path: str, token: str | None = None, **kwargs) -> Any:
    with _client(token) as client:
        response = _send(client, method, path, **kwargs)
        if response.is_error:
            raise ApiError(response.status_code, _detail(response))
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()


def health() -> dict[str, Any]:
    return _request("GET", "/health")


def transactions_sample() -> bytes:
    with _client() as client:
        response = _send(client, "GET", "/uploads/transactions-sample")
        if response.is_error:
            raise ApiError(response.status_code, _detail(response))
        return response.content


def register(email: str, username: str, full_name: str, password: str, password_confirm: str) -> dict[str, Any]:
    payload = {
        "email": email,
        "username": username,
        "full_name": full_name,
        "password": password,
        "password_confirm": password_confirm,
    }
    if AUTH_API_URL:
        with httpx.Client(timeout=30.0) as client:
            response = _send(client, "POST", f"{AUTH_API_URL}/auth/register", json=payload)
            if response.is_error:
                raise ApiError(response.status_code, _detail(response))
            return response.json()
    return _request("POST", "/auth/register", json=payload)


def signin(username: str, password: str, remember_me: bool = False) -> dict[str, Any]:
    payload = {"username": username, "password": password, "remember_me": remember_me}
    if AUTH_API_URL:
        with httpx.Client(timeout=30.0) as client:
            response = _send(client, "POST", f"{AUTH_API_URL}/auth/signin", json=payload)
            if response.is_error:
                raise ApiError(response.status_code, _detail(response))
            return response.json()
    return _request("POST", "/auth/signin", json=payload)


def me(token: str) -> dict[str, Any]:
    return _request("GET", "/users/me", token=token)


def login_history(token: str, limit: int = 50) -> dict[str, Any]:
    return _request("GET", "/auth/login-history", token=token, params={"limit": limit})


def forgot_password(email: str) -> dict[str, Any]:
    return _request("POST", "/users/forgot-password", json={"email": email})


def reset_password(token: str, email: str, password: str, password_confirm: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/users/reset-password",
        json={
            "token": token,
            "email": email,
            "password": password,
            "passwordConfirm": password_confirm,
        },
    )


def list_blocked_ips(token: str) -> dict[str, Any]:
    return _request("GET", "/auth/blocked-ips", token=token)


def block_ip(token: str, ip: str) -> dict[str, Any]:
    return _request("POST", "/auth/blocked-ips", token=token, json={"ip": ip})


def unblock_ip(token: str, ip: str) -> dict[str, Any]:
    return _request("DELETE", "/auth/blocked-ips", token=token, json={"ip": ip})
