"""Function URL handler for sign-in and sign-up (HTTP API payload 2.0 event shape).

Sign-in writes login history via AuthService → DynamoDB PutItem.
Sign-up writes Users via RegistrationService → DynamoDB PutItem.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from core.exceptions import IpBlockedForUser, IpRestricted, RegistrationConflict, UserLockedOut
from core.settings import get_settings
from pydantic import ValidationError
from schema.auth import CreateUserRegistration, CredentialsRequest, TokenResponse
from services.auth_service import AuthService
from services.registration import RegistrationService


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _headers(event: dict[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}


def caller_ip(event: dict[str, Any]) -> str:
    headers = _headers(event)
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    ctx = event.get("requestContext") or {}
    http = ctx.get("http") or {}
    if http.get("sourceIp"):
        return str(http["sourceIp"])
    identity = ctx.get("identity") or {}
    return str(identity.get("sourceIp") or "unknown")


def user_agent(event: dict[str, Any]) -> str:
    return _headers(event).get("user-agent") or ""


def _parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded") and isinstance(raw, str):
        raw = base64.b64decode(raw).decode("utf-8")
    payload = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(payload, dict):
        raise ValueError("body must be a JSON object")
    return payload


def _method(event: dict[str, Any]) -> str:
    return str(
        ((event.get("requestContext") or {}).get("http") or {}).get("method")
        or event.get("httpMethod")
        or "POST"
    ).upper()


def _path(event: dict[str, Any]) -> str:
    path = (
        event.get("rawPath")
        or ((event.get("requestContext") or {}).get("http") or {}).get("path")
        or "/"
    )
    return f"/{str(path).strip('/')}"


def _signin(event: dict[str, Any]) -> dict[str, Any]:
    try:
        data = CredentialsRequest.model_validate(_parse_json_body(event))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, ValidationError, TypeError):
        return _response(400, {"detail": "Invalid request body"})

    try:
        token = AuthService().authenticate(
            data.username,
            data.password,
            data.remember_me,
            caller_ip(event),
            user_agent(event),
        )
    except UserLockedOut:
        return _response(423, {"detail": "User is locked out"})
    except IpBlockedForUser:
        return _response(403, {"detail": "This IP is blocked for this account"})
    except IpRestricted:
        return _response(429, {"detail": "Too many failed logins from this IP"})
    except LookupError:
        return _response(401, {"detail": "Incorrect username or password"})

    return _response(200, TokenResponse.respond(token))


def _register(event: dict[str, Any]) -> dict[str, Any]:
    if not get_settings().allow_signup:
        return _response(403, {"detail": "User registration is disabled"})

    try:
        data = CreateUserRegistration.model_validate(_parse_json_body(event))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, ValidationError, TypeError):
        return _response(400, {"detail": "Invalid request body"})

    try:
        user = RegistrationService().register_user(data)
    except RegistrationConflict as exc:
        return _response(409, {"detail": str(exc)})

    return _response(201, user.model_dump(mode="json"))


def lambda_handler(event: dict[str, Any], _context: Any = None) -> dict[str, Any]:
    """Dispatch Function URL requests to sign-in or sign-up."""
    if _method(event) == "OPTIONS":
        return {"statusCode": 204, "headers": {"content-type": "application/json"}, "body": ""}
    if _method(event) != "POST":
        return _response(405, {"detail": "Method not allowed"})

    path = _path(event)
    if path == "/auth/signin":
        return _signin(event)
    if path == "/auth/register":
        return _register(event)
    return _response(404, {"detail": "Not found"})
