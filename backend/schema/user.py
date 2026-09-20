from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from core.settings import get_settings


def mask_phone(phone: str) -> str:
    """Public hint only; never return the full number."""
    digits = (phone or "").strip()
    if len(digits) < 6:
        return ""
    return f"{digits[:3]} *** *** {digits[-3:]}"


class UserOut(BaseModel):
    user_id: str
    email: str
    username: str
    full_name: str
    created_at: datetime
    phone_hint: str = ""
    two_factor_enabled: bool = False
    is_admin: bool = False
    notify_email: bool = False

    @classmethod
    def from_record(cls, user: "UserRecord") -> "UserOut":
        enabled = bool(user.two_factor_enabled and user.phone_verified and user.phone)
        return cls(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            created_at=user.created_at,
            phone_hint=mask_phone(user.phone) if enabled else "",
            two_factor_enabled=enabled,
            is_admin=bool(user.is_admin),
            notify_email=bool(user.notify_email),
        )


class UserRecord(UserOut):
    password_hash: str
    login_attempts: int = 0
    locked_at: datetime | None = None
    blocked_ips: list[str] = Field(default_factory=list)
    phone: str = ""
    phone_verified: bool = False
    sns_email_subscription_arn: str = ""

    @property
    def is_locked(self) -> bool:
        if self.locked_at is None:
            return False
        locked_at = self.locked_at if self.locked_at.tzinfo else self.locked_at.replace(tzinfo=UTC)
        expires = locked_at + timedelta(hours=get_settings().security_user_lockout_hours)
        return expires > datetime.now(UTC)


class AnalysisNotificationsIn(BaseModel):
    email: bool


class LoginEvent(BaseModel):
    event_id: str
    user_id: str
    username: str
    ip: str
    success: bool
    user_agent: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PasswordResetRecord(BaseModel):
    token: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self) -> bool:
        created = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=UTC)
        expires = created + timedelta(hours=get_settings().password_reset_token_hours)
        return datetime.now(UTC) >= expires


class OtpRecord(BaseModel):
    email: str
    phone: str
    code_hash: str
    purpose: str
    user_id: str = ""
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_expired(self) -> bool:
        created = self.created_at if self.created_at.tzinfo else self.created_at.replace(tzinfo=UTC)
        expires = created + timedelta(seconds=get_settings().otp_ttl_seconds)
        return datetime.now(UTC) >= expires
