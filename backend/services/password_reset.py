"""Forgot-password and email reset."""

from __future__ import annotations

import logging

from fastapi import HTTPException, status

from core.security.hasher import get_hasher
from core.security.tokens import url_safe_token
from core.settings import get_settings
from schema.user import PasswordResetRecord
from services.email import EmailService
from services.user_store import UserStore, get_user_store

logger = logging.getLogger("password_reset")


class PasswordResetService:
    def __init__(self, store: UserStore | None = None, email: EmailService | None = None) -> None:
        self.store = store or get_user_store()
        self.email = email or EmailService()
        self.settings = get_settings()

    def generate_reset_token(self, email: str) -> PasswordResetRecord | None:
        user = self.store.get_by_email(email)
        if user is None:
            logger.error("failed to create password reset for email=%s: user does not exist", email)
            return None

        record = PasswordResetRecord(user_id=user.user_id, token=url_safe_token())
        return self.store.save_reset_token(record)

    def send_reset_email(self, email: str) -> None:
        token_entry = self.generate_reset_token(email)
        if token_entry is None:
            return None

        reset_url = self.settings.password_reset_url(token_entry.token)
        try:
            sent = self.email.send_forgot_password(email, reset_url)
        except Exception:
            logger.exception("failed to send reset email to %s", email)
            return
        if not sent:
            logger.error(
                "failed to send reset email to %s (SMTP not configured or send returned false)",
                email,
            )
            return
        logger.info("password reset email sent to %s", email)

    def reset_password(self, token: str, new_password: str) -> None:
        token_entry = self.store.get_reset_token(token)
        if token_entry is None or token_entry.is_expired():
            if token_entry is not None:
                self.store.delete_reset_token(token)
            logger.error("failed to reset password: invalid token")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid token")

        user = self.store.get_by_id(token_entry.user_id)
        if user is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid token")

        user.password_hash = get_hasher().hash(new_password)
        user.login_attempts = 0
        user.locked_at = None
        self.store.patch(
            user.user_id,
            password_hash=user.password_hash,
            login_attempts=0,
            locked_at=None,
        )
        self.store.delete_reset_token(token)
