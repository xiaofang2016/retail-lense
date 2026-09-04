"""Optional SMS 2FA. Phone is bound after login; registration is unchanged."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from core.exceptions import TwoFactorError
from core.settings import get_settings
from schema.user import OtpRecord, UserRecord, mask_phone
from services.sns import get_sns_sender
from services.user_store import UserStore, get_user_store

logger = logging.getLogger("two_factor")

PURPOSE_BIND = "bind"
PURPOSE_LOGIN = "login"


def _hash_code(code: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, code.encode("utf-8"), hashlib.sha256).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


class TwoFactorService:
    def __init__(self, store: UserStore | None = None) -> None:
        self.store = store or get_user_store()
        self.settings = get_settings()
        self.sns = get_sns_sender()

    def _send(self, *, email: str, phone: str, purpose: str, user_id: str) -> None:
        existing = self.store.get_otp(email)
        logger.debug("existing otp record for %s: %s", email, existing)
        if existing is not None and not existing.is_expired():
            created = existing.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            wait = datetime.now(UTC) - created
            if wait < timedelta(seconds=self.settings.otp_resend_seconds):
                raise TwoFactorError("Wait before requesting another code", 429)

        code = _generate_code()
        record = OtpRecord(
            email=email.lower(),
            phone=phone,
            code_hash=_hash_code(code),
            purpose=purpose,
            user_id=user_id,
        )
        self.store.save_otp(record)
        logger.info("saved otp record for %s: %s", email, record)
        try:
            self.sns.publish_otp(phone, code)
            logger.info("sent otp sms to %s code=%s (purpose=%s)", phone, code, purpose)
        except TwoFactorError:
            raise
        except Exception as exc:
            self.store.delete_otp(email)
            logger.error("failed to send otp sms: %s", exc)
            raise TwoFactorError("Failed to send verification code", 500) from exc

    def _check(self, email: str, code: str, purpose: str) -> OtpRecord:
        record = self.store.get_otp(email)
        if record is None or record.purpose != purpose or record.is_expired():
            if record is not None:
                self.store.delete_otp(email)
            raise TwoFactorError("Invalid or expired code", 400)
        if not hmac.compare_digest(record.code_hash, _hash_code(code)):
            record.attempts += 1
            if record.attempts >= self.settings.otp_max_attempts:
                self.store.delete_otp(email)
                raise TwoFactorError("Too many attempts. Request a new code", 400)
            self.store.save_otp(record)
            raise TwoFactorError("Invalid or expired code", 400)
        return record

    def start_bind(self, user: UserRecord, phone: str) -> str:
        other = self.store.get_by_phone(phone)
        if other is not None and other.user_id != user.user_id:
            raise TwoFactorError("phone already in use", 409)
        self._send(email=user.email, phone=phone, purpose=PURPOSE_BIND, user_id=user.user_id)
        return mask_phone(phone)

    def confirm_bind(self, user: UserRecord, code: str) -> UserRecord:
        record = self._check(user.email, code, PURPOSE_BIND)
        fresh = self.store.get_by_id(user.user_id) or user
        fresh.phone = record.phone
        fresh.phone_verified = True
        fresh.two_factor_enabled = True
        self.store.delete_otp(user.email)
        return self.store.update(fresh)

    def disable(self, user: UserRecord) -> UserRecord:
        fresh = self.store.get_by_id(user.user_id) or user
        fresh.phone = ""
        fresh.phone_verified = False
        fresh.two_factor_enabled = False
        self.store.delete_otp(fresh.email)
        return self.store.update(fresh)

    def send_login_otp(self, user: UserRecord) -> str:
        self._send(email=user.email, phone=user.phone, purpose=PURPOSE_LOGIN, user_id=user.user_id)
        return mask_phone(user.phone)

    def consume_login(self, user: UserRecord, code: str) -> None:
        self._check(user.email, code, PURPOSE_LOGIN)
        self.store.delete_otp(user.email)
