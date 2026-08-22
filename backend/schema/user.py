from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from core.settings import get_settings


class UserOut(BaseModel):
    user_id: str
    email: str
    username: str
    full_name: str
    created_at: datetime


class UserRecord(UserOut):
    password_hash: str
    login_attempts: int = 0
    locked_at: datetime | None = None
    blocked_ips: list[str] = Field(default_factory=list)

    @property
    def is_locked(self) -> bool:
        if self.locked_at is None:
            return False
        locked_at = self.locked_at if self.locked_at.tzinfo else self.locked_at.replace(tzinfo=UTC)
        expires = locked_at + timedelta(hours=get_settings().security_user_lockout_hours)
        return expires > datetime.now(UTC)


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
