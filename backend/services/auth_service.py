"""Credential login, lockout, login history, and per-IP failed-attempt limits."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.exceptions import IpBlockedForUser, IpRestricted, UserLockedOut
from core.security.hasher import FAKE_PASSWORD_HASH, get_hasher
from core.security.ip import normalize_ip
from core.security.tokens import create_access_token
from core.settings import get_settings
from schema.user import LoginEvent, UserOut, UserRecord
from services.user_store import UserStore, get_user_store


class AuthService:
    def __init__(self, store: UserStore | None = None) -> None:
        self.store = store or get_user_store()
        self.settings = get_settings()

    def try_get_user(self, username: str) -> UserRecord | None:
        user = self.store.get_by_username(username)
        if user:
            return user
        return self.store.get_by_email(username)

    def _record_event(
        self,
        *,
        user_id: str,
        username: str,
        ip: str,
        success: bool,
        user_agent: str,
    ) -> None:
        self.store.add_login_event(
            LoginEvent(
                event_id=str(uuid4()),
                user_id=user_id,
                username=username.lower(),
                ip=ip,
                success=success,
                user_agent=user_agent,
                created_at=datetime.now(UTC),
            )
        )

    def _enforce_ip_limit(self, ip: str) -> None:
        window = datetime.now(UTC) - timedelta(minutes=self.settings.security_ip_window_minutes)
        failed = self.store.count_failed_by_ip(ip, window)
        if failed >= self.settings.security_max_failed_per_ip:
            raise IpRestricted()

    def _unlock_if_expired(self, user: UserRecord) -> UserRecord:
        """Clear lockout once the lock window has elapsed."""
        if user.locked_at is not None and not user.is_locked:
            user.locked_at = None
            user.login_attempts = 0
            return self.store.update(user)
        return user

    def lock_user(self, user: UserRecord) -> UserRecord:
        user.locked_at = datetime.now(UTC)
        return self.store.update(user)

    def unlock_user(self, user: UserRecord) -> UserRecord:
        user.locked_at = None
        user.login_attempts = 0
        return self.store.update(user)

    def _ip_blocked(self, user: UserRecord, ip: str) -> bool:
        try:
            caller = normalize_ip(ip)
        except ValueError:
            caller = ip.strip()
        blocked = set()
        for item in user.blocked_ips:
            try:
                blocked.add(normalize_ip(item))
            except ValueError:
                blocked.add(item.strip())
        return caller in blocked

    def list_blocked_ips(self, user: UserRecord) -> list[str]:
        fresh = self.store.get_by_id(user.user_id) or user
        return list(fresh.blocked_ips)

    def block_ip(self, user: UserRecord, ip: str) -> UserRecord:
        try:
            ip = normalize_ip(ip)
        except ValueError as exc:
            raise ValueError("invalid IP") from exc
        fresh = self.store.get_by_id(user.user_id) or user
        if ip not in fresh.blocked_ips:
            fresh.blocked_ips = [*fresh.blocked_ips, ip]
            fresh = self.store.update(fresh)
        return fresh

    def unblock_ip(self, user: UserRecord, ip: str) -> UserRecord:
        try:
            ip = normalize_ip(ip)
        except ValueError as exc:
            raise ValueError("invalid IP") from exc
        fresh = self.store.get_by_id(user.user_id) or user
        fresh.blocked_ips = [item for item in fresh.blocked_ips if item != ip]
        return self.store.update(fresh)

    def authenticate(self, username: str, password: str, remember_me: bool, ip: str, user_agent: str = "") -> str:
        self._enforce_ip_limit(ip)

        user = self.try_get_user(username)
        hasher = get_hasher()

        if not user:
            hasher.verify("abc123cba321", FAKE_PASSWORD_HASH)
            self._record_event(user_id="unknown", username=username, ip=ip, success=False, user_agent=user_agent)
            raise LookupError("invalid credentials")

        user = self._unlock_if_expired(user)

        if self._ip_blocked(user, ip):
            self._record_event(user_id=user.user_id, username=username, ip=ip, success=False, user_agent=user_agent)
            raise IpBlockedForUser()

        if user.login_attempts >= self.settings.security_max_login_attempts or user.is_locked:
            self._record_event(user_id=user.user_id, username=username, ip=ip, success=False, user_agent=user_agent)
            raise UserLockedOut()

        if not hasher.verify(password, user.password_hash):
            user.login_attempts += 1
            self.store.update(user)
            if user.login_attempts >= self.settings.security_max_login_attempts:
                self.lock_user(user)
            self._record_event(user_id=user.user_id, username=username, ip=ip, success=False, user_agent=user_agent)
            raise LookupError("invalid credentials")

        user.login_attempts = 0
        self.store.update(user)
        self._record_event(user_id=user.user_id, username=username, ip=ip, success=True, user_agent=user_agent)
        return create_access_token(user.user_id, remember_me=remember_me)

    def list_history(self, user_id: str, limit: int = 50) -> list[LoginEvent]:
        return self.store.list_login_events(user_id, limit=limit)

    def to_public(self, user: UserRecord) -> UserOut:
        return UserOut(
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            created_at=user.created_at,
        )
