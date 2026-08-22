"""Email delivery. SMTP (Mailpit locally, real SMTP on EC2); in-memory outbox as fallback."""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formatdate
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

from core.settings import get_settings

logger = logging.getLogger("email")

SMTP_TIMEOUT = 10


@dataclass
class OutgoingEmail:
    to: str
    subject: str
    html: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EmailSender(Protocol):
    def send(self, email_to: str, subject: str, html: str) -> bool: ...


class MemoryEmailSender:
    def __init__(self) -> None:
        self.outbox: list[OutgoingEmail] = []

    def send(self, email_to: str, subject: str, html: str) -> bool:
        self.outbox.append(OutgoingEmail(to=email_to, subject=subject, html=html))
        return True

    def clear(self) -> None:
        self.outbox.clear()


class SmtpEmailSender:
    def send(self, email_to: str, subject: str, html: str) -> bool:
        settings = get_settings()
        if not settings.smtp_from_email or not settings.smtp_host:
            raise ValueError("SMTP_HOST and SMTP_FROM_EMAIL must be set")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        msg["To"] = email_to
        msg["Date"] = formatdate(localtime=True)
        try:
            domain = settings.smtp_from_email.split("@", 1)[1]
        except IndexError:
            domain = settings.smtp_from_email
        msg["Message-ID"] = f"<{uuid4()}@{domain}>"
        msg.set_content("Open this message in an HTML client to reset your password.")
        msg.add_alternative(html, subtype="html")

        strategy = (settings.smtp_auth_strategy or "TLS").upper()
        if strategy == "SSL":
            server: smtplib.SMTP = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT)

        with server:
            if strategy == "TLS":
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            errors = server.send_message(msg)

        success = errors == {}
        if not success:
            logger.error("send email error: %s", errors)
        return success


class EmailService:
    def __init__(self, sender: EmailSender | None = None) -> None:
        self.sender = sender or get_email_sender()
        self.settings = get_settings()

    def send_forgot_password(self, address: str, reset_password_url: str) -> bool:
        if not self.settings.smtp_enabled() and not self.settings.is_local():
            return False
        html = (
            "<p>A password reset was requested for your Retail Lense account.</p>"
            f'<p><a href="{reset_password_url}">Reset your password</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        )
        return self.sender.send(address, "Retail Lense Forgot Password", html)


@lru_cache(maxsize=1)
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.app_env == "test":
        return MemoryEmailSender()
    if settings.smtp_enabled():
        return SmtpEmailSender()
    return MemoryEmailSender()
