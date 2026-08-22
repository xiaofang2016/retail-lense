"""HTTP client for the FastAPI backend. JWT stays in Streamlit session_state."""

from __future__ import annotations

import os
from typing import Any

import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


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


def _request(method: str, path: str, token: str | None = None, **kwargs) -> Any:
    with _client(token) as client:
        response = client.request(method, path, **kwargs)
        if response.is_error:
            raise ApiError(response.status_code, _detail(response))
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()


def health() -> dict[str, Any]:
    return _request("GET", "/health")


def register(email: str, username: str, full_name: str, password: str, password_confirm: str) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "full_name": full_name,
            "password": password,
            "password_confirm": password_confirm,
        },
    )


def signin(username: str, password: str, remember_me: bool = False) -> dict[str, Any]:
    return _request(
        "POST",
        "/auth/signin",
        json={"username": username, "password": password, "remember_me": remember_me},
    )


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
