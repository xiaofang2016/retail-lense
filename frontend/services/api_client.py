"""HTTP client for the FastAPI backend. JWT stays in Streamlit session_state."""

from __future__ import annotations

import logging
import os
import socket
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

import httpx

from services.client_ip import CLIENT_IP_HEADER, browser_ip, browser_user_agent

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1"}


def auth_api_url() -> str:
    """Lambda Function URL for sign-in/sign-up. Empty = FastAPI.

    Read at call time so EC2 can inject AUTH_API_URL from Secrets Manager
    after this module is imported.
    """
    return os.getenv("AUTH_API_URL", "").strip().rstrip("/")


# Back-compat for tests/patches that still set the module attribute.
AUTH_API_URL = auth_api_url()

logger = logging.getLogger("retaillen.frontend.http")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _in_docker() -> bool:
    return Path("/.dockerenv").exists()


def backend_url() -> str:
    """Read BACKEND_URL on each request (not at import).

    Compose interpolates the host .env. `http://localhost:8000` inside a
    container is this process, not FastAPI. `http://backend:8000` only
    resolves when the API service is on the same Compose network.
    """
    raw = (os.getenv("BACKEND_URL") or BACKEND_URL or "http://localhost:8000").strip()
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if _in_docker() and host in _LOOPBACK_HOSTS:
        netloc = f"host.docker.internal:{parsed.port}" if parsed.port else "host.docker.internal"
        raw = urlunparse(parsed._replace(netloc=netloc))
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        logger.info("rewrote loopback BACKEND_URL to %s", raw)
    if host:
        try:
            socket.getaddrinfo(host, parsed.port or 80)
        except socket.gaierror as exc:
            raise ApiError(
                503,
                f"Cannot resolve API host {host!r} from BACKEND_URL={raw}. "
                "On a frontend-only EC2 set BACKEND_URL to the backend private IP "
                "(e.g. http://172.31.37.113:8000), then "
                "docker compose up -d --force-recreate --no-deps frontend. "
                "On a laptop Compose stack use BACKEND_URL=http://backend:8000.",
            ) from exc
    return raw


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
    return httpx.Client(base_url=backend_url(), timeout=30.0, headers=headers)


def _send(client: httpx.Client, method: str, url: str, **kwargs) -> httpx.Response:
    request_id = uuid4().hex[:12]
    request = client.build_request(method, url, **kwargs)
    request.headers["x-request-id"] = request_id
    # Streamlit→API is a new TCP connection; without this, FastAPI/Lambda see the
    # frontend private IP and per-account IP blocks never match the browser.
    client_ip = browser_ip()
    if client_ip:
        request.headers["x-forwarded-for"] = client_ip
        request.headers[CLIENT_IP_HEADER] = client_ip
    user_agent = browser_user_agent()
    if user_agent:
        request.headers["user-agent"] = user_agent
    safe_url = str(request.url).split("?", 1)[0]
    started = time.monotonic()
    logger.info("request_id=%s method=%s url=%s event=request_started", request_id, method.upper(), safe_url)
    try:
        response = client.send(request)
    except httpx.RequestError as exc:
        elapsed_ms = round((time.monotonic() - started) * 1000)
        logger.error(
            "request_id=%s method=%s url=%s duration_ms=%s error_type=%s event=request_failed",
            request_id,
            method.upper(),
            safe_url,
            elapsed_ms,
            type(exc).__name__,
        )
        raise ApiError(
            503,
            f"Cannot reach API at {safe_url}. Check BACKEND_URL and that FastAPI is running.",
        ) from exc
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
    lambda_url = auth_api_url() or AUTH_API_URL
    if lambda_url:
        with httpx.Client(timeout=30.0) as client:
            response = _send(client, "POST", f"{lambda_url}/auth/register", json=payload)
            if response.is_error:
                raise ApiError(response.status_code, _detail(response))
            return response.json()
    return _request("POST", "/auth/register", json=payload)


def signin(username: str, password: str, remember_me: bool = False) -> dict[str, Any]:
    payload = {"username": username, "password": password, "remember_me": remember_me}
    lambda_url = auth_api_url() or AUTH_API_URL
    if lambda_url:
        with httpx.Client(timeout=30.0) as client:
            response = _send(client, "POST", f"{lambda_url}/auth/signin", json=payload)
            if response.is_error:
                raise ApiError(response.status_code, _detail(response))
            return response.json()
    return _request("POST", "/auth/signin", json=payload)


def verify_otp(username: str, code: str, remember_me: bool = False) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/verify-otp",
        json={"username": username, "code": code, "remember_me": remember_me},
    )


def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    return _request("POST", "/auth/refresh", json={"refresh_token": refresh_token})


def start_phone_2fa(token: str, phone: str) -> dict[str, Any]:
    return _request("POST", "/auth/2fa/phone", token=token, json={"phone": phone})


def confirm_phone_2fa(token: str, code: str) -> dict[str, Any]:
    return _request("POST", "/auth/2fa/confirm", token=token, json={"code": code})


def disable_2fa(token: str) -> dict[str, Any]:
    return _request("POST", "/auth/2fa/disable", token=token)


def me(token: str) -> dict[str, Any]:
    return _request("GET", "/users/me", token=token)


def set_analysis_notifications(token: str, email: bool) -> dict[str, Any]:
    """Subscribe or unsubscribe the account email on the analysis-complete SNS topic."""
    return _request("PUT", "/users/me/analysis-notifications", token=token, json={"email": email})


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


def create_analysis(token: str, file_extension: str, file_name: str, file_size_bytes: int) -> dict[str, Any]:
    return _request(
        "POST",
        "/analyses",
        token=token,
        json={
            "file_extension": file_extension,
            "file_name": file_name,
            "file_size_bytes": file_size_bytes,
        },
    )


def upload_bytes_to_presigned_url(upload_url: str, body: bytes, content_type: str) -> None:
    """PUT straight to S3 using the presigned URL -- bypasses the backend entirely."""
    response = httpx.put(upload_url, content=body, headers={"Content-Type": content_type}, timeout=60.0)
    if response.is_error:
        raise ApiError(response.status_code, response.text or f"HTTP {response.status_code}")


def get_analysis_status(token: str, analysis_id: str) -> dict[str, Any]:
    return _request("GET", f"/analyses/{analysis_id}/status", token=token)


def list_analyses(token: str) -> dict[str, Any]:
    return _request("GET", "/analyses", token=token)


def get_analysis_report(token: str, analysis_id: str) -> dict[str, Any]:
    return _request("GET", f"/analyses/{analysis_id}/report", token=token)

def delete_analysis(token: str, analysis_id: str) -> None:
    _request("DELETE", f"/analyses/{analysis_id}", token=token)