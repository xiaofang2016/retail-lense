"""Typed shapes for Users / Analyses items stored in DynamoDB."""

from __future__ import annotations

from typing import TypedDict


class UserItem(TypedDict):
    user_id: str
    email: str
    username: str
    full_name: str
    password_hash: str
    login_attempts: int
    locked_at: str | None
    created_at: str
    blocked_ips: list[str]


class LoginHistoryItem(TypedDict):
    user_id: str
    sk: str
    event_id: str
    username: str
    ip: str
    success: bool
    user_agent: str
    created_at: str


class PasswordResetItem(TypedDict):
    token: str
    user_id: str
    created_at: str
    ttl: int


class AnalysisItem(TypedDict):
    analysis_id: str
    user_id: str
    # pending -> validation -> processing -> done, or failed at any stage.
    status: str
    k: int
    s3_upload_key: str
    s3_result_key: str
    # Set only when status == "failed"; explains what went wrong (validation or processing).
    error_message: str | None
    # Set at creation; needed for the Analysis Library's date/filename search and sort UI.
    created_at: str
    original_filename: str
