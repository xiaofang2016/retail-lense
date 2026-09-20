"""User and login-history persistence. Memory when APP_ENV=test or no DDB_ENDPOINT; DynamoDB otherwise."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from functools import lru_cache
from typing import Protocol

from core.settings import get_settings
from schema.user import LoginEvent, OtpRecord, PasswordResetRecord, UserRecord


class UserStore(Protocol):
    def get_by_id(self, user_id: str) -> UserRecord | None: ...

    def get_by_username(self, username: str) -> UserRecord | None: ...

    def get_by_email(self, email: str) -> UserRecord | None: ...

    def create(self, user: UserRecord) -> UserRecord: ...

    def update(self, user: UserRecord) -> UserRecord: ...

    def add_login_event(self, event: LoginEvent) -> LoginEvent: ...

    def list_login_events(self, user_id: str, limit: int = 50) -> list[LoginEvent]: ...

    def count_failed_by_ip(self, ip: str, since: datetime) -> int: ...

    def save_reset_token(self, record: PasswordResetRecord) -> PasswordResetRecord: ...

    def get_reset_token(self, token: str) -> PasswordResetRecord | None: ...

    def delete_reset_token(self, token: str) -> None: ...

    def get_by_phone(self, phone: str) -> UserRecord | None: ...

    def save_otp(self, record: OtpRecord) -> OtpRecord: ...

    def get_otp(self, email: str) -> OtpRecord | None: ...

    def delete_otp(self, email: str) -> None: ...

    def reset(self) -> None: ...


def _parse_dt(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class MemoryUserStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: dict[str, UserRecord] = {}
        self._events: list[LoginEvent] = []
        self._reset_tokens: dict[str, PasswordResetRecord] = {}
        self._otps: dict[str, OtpRecord] = {}

    def reset(self) -> None:
        with self._lock:
            self._by_id.clear()
            self._events.clear()
            self._reset_tokens.clear()
            self._otps.clear()

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self._by_id.get(user_id)

    def get_by_username(self, username: str) -> UserRecord | None:
        key = username.lower()
        for user in self._by_id.values():
            if user.username.lower() == key:
                return user
        return None

    def get_by_email(self, email: str) -> UserRecord | None:
        key = email.lower()
        for user in self._by_id.values():
            if user.email.lower() == key:
                return user
        return None

    def create(self, user: UserRecord) -> UserRecord:
        with self._lock:
            self._by_id[user.user_id] = user
        return user

    def update(self, user: UserRecord) -> UserRecord:
        with self._lock:
            self._by_id[user.user_id] = user
        return user

    def add_login_event(self, event: LoginEvent) -> LoginEvent:
        with self._lock:
            self._events.append(event)
        return event

    def list_login_events(self, user_id: str, limit: int = 50) -> list[LoginEvent]:
        items = [(index, event) for index, event in enumerate(self._events) if event.user_id == user_id]
        items.sort(key=lambda pair: (pair[1].created_at, pair[0]), reverse=True)
        return [event for _, event in items[:limit]]

    def count_failed_by_ip(self, ip: str, since: datetime) -> int:
        count = 0
        for event in self._events:
            created = event.created_at if event.created_at.tzinfo else event.created_at.replace(tzinfo=UTC)
            if event.ip == ip and not event.success and created >= since:
                count += 1
        return count

    def save_reset_token(self, record: PasswordResetRecord) -> PasswordResetRecord:
        with self._lock:
            self._reset_tokens[record.token] = record
        return record

    def get_reset_token(self, token: str) -> PasswordResetRecord | None:
        return self._reset_tokens.get(token)

    def delete_reset_token(self, token: str) -> None:
        with self._lock:
            self._reset_tokens.pop(token, None)

    def get_by_phone(self, phone: str) -> UserRecord | None:
        key = (phone or "").strip()
        if not key:
            return None
        for user in self._by_id.values():
            if user.phone_verified and user.phone == key:
                return user
        return None

    def save_otp(self, record: OtpRecord) -> OtpRecord:
        with self._lock:
            self._otps[record.email.lower()] = record
        return record

    def get_otp(self, email: str) -> OtpRecord | None:
        return self._otps.get(email.lower())

    def delete_otp(self, email: str) -> None:
        with self._lock:
            self._otps.pop(email.lower(), None)


class DynamoUserStore:
    def __init__(self) -> None:
        from services.dynamodb import dynamodb_resource

        settings = get_settings()
        self._ddb = dynamodb_resource()
        self._users = self._ddb.Table(settings.ddb_users_table)
        self._history = self._ddb.Table(settings.ddb_login_history_table)
        self._resets = self._ddb.Table(settings.ddb_password_reset_table)
        self._otps = self._ddb.Table(settings.ddb_otps_table)

    def reset(self) -> None:
        raise RuntimeError("reset() is only supported on the in-memory store")

    def _item_to_user(self, item: dict) -> UserRecord:
        return UserRecord(
            user_id=item["user_id"],
            email=item["email"],
            username=item["username"],
            full_name=item["full_name"],
            password_hash=item["password_hash"],
            login_attempts=int(item.get("login_attempts") or 0),
            locked_at=_parse_dt(item.get("locked_at")),
            created_at=_parse_dt(item["created_at"]) or datetime.now(UTC),
            blocked_ips=[str(ip) for ip in (item.get("blocked_ips") or [])],
            phone=str(item.get("phone") or ""),
            phone_verified=bool(item.get("phone_verified")),
            two_factor_enabled=bool(item.get("two_factor_enabled")),
            is_admin=bool(item.get("is_admin")),
            notify_email=bool(item.get("notify_email")),
            sns_email_subscription_arn=str(item.get("sns_email_subscription_arn") or ""),
        )

    def get_by_id(self, user_id: str) -> UserRecord | None:
        response = self._users.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        return self._item_to_user(item) if item else None

    def get_by_username(self, username: str) -> UserRecord | None:
        response = self._users.query(
            IndexName="UsernameIndex",
            KeyConditionExpression="username = :u",
            ExpressionAttributeValues={":u": username.lower()},
            Limit=1,
        )
        items = response.get("Items") or []
        return self._item_to_user(items[0]) if items else None

    def get_by_email(self, email: str) -> UserRecord | None:
        response = self._users.query(
            IndexName="EmailIndex",
            KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": email.lower()},
            Limit=1,
        )
        items = response.get("Items") or []
        return self._item_to_user(items[0]) if items else None

    def _user_item(self, user: UserRecord) -> dict:
        item = {
            "user_id": user.user_id,
            "email": user.email.lower(),
            "username": user.username.lower(),
            "full_name": user.full_name,
            "password_hash": user.password_hash,
            "login_attempts": user.login_attempts,
            "created_at": user.created_at.isoformat(),
            "blocked_ips": list(user.blocked_ips),
            "phone": user.phone or "",
            "phone_verified": bool(user.phone_verified),
            "two_factor_enabled": bool(user.two_factor_enabled),
            "is_admin": bool(user.is_admin),
            "notify_email": bool(user.notify_email),
            "sns_email_subscription_arn": user.sns_email_subscription_arn or "",
        }
        if user.locked_at:
            item["locked_at"] = user.locked_at.isoformat()
        return item

    def create(self, user: UserRecord) -> UserRecord:
        self._users.put_item(Item=self._user_item(user))
        return user

    def update(self, user: UserRecord) -> UserRecord:
        self._users.put_item(Item=self._user_item(user))
        return user

    def add_login_event(self, event: LoginEvent) -> LoginEvent:
        created_at = event.created_at.isoformat(timespec="microseconds")
        self._history.put_item(
            Item={
                "user_id": event.user_id,
                "sk": f"{created_at}#{event.event_id}",
                "event_id": event.event_id,
                "username": event.username,
                "ip": event.ip,
                "success": event.success,
                "user_agent": event.user_agent,
                "created_at": created_at,
            }
        )
        return event

    def list_login_events(self, user_id: str, limit: int = 50) -> list[LoginEvent]:
        response = self._history.query(
            KeyConditionExpression="user_id = :u",
            ExpressionAttributeValues={":u": user_id},
            ScanIndexForward=False,
            Limit=limit,
        )
        events: list[LoginEvent] = []
        for item in response.get("Items") or []:
            events.append(
                LoginEvent(
                    event_id=item["event_id"],
                    user_id=item["user_id"],
                    username=item["username"],
                    ip=item["ip"],
                    success=bool(item["success"]),
                    user_agent=item.get("user_agent") or "",
                    created_at=_parse_dt(item["created_at"]) or datetime.now(UTC),
                )
            )
        return events

    def count_failed_by_ip(self, ip: str, since: datetime) -> int:
        response = self._history.query(
            IndexName="IpIndex",
            KeyConditionExpression="ip = :ip AND created_at >= :since",
            FilterExpression="success = :false",
            ExpressionAttributeValues={
                ":ip": ip,
                ":since": since.isoformat(),
                ":false": False,
            },
            Select="COUNT",
        )
        return int(response.get("Count") or 0)

    def save_reset_token(self, record: PasswordResetRecord) -> PasswordResetRecord:
        ttl = int(record.created_at.timestamp()) + get_settings().password_reset_token_hours * 3600
        self._resets.put_item(
            Item={
                "token": record.token,
                "user_id": record.user_id,
                "created_at": record.created_at.isoformat(),
                "ttl": ttl,
            }
        )
        return record

    def get_reset_token(self, token: str) -> PasswordResetRecord | None:
        response = self._resets.get_item(Key={"token": token})
        item = response.get("Item")
        if not item:
            return None
        return PasswordResetRecord(
            token=item["token"],
            user_id=item["user_id"],
            created_at=_parse_dt(item["created_at"]) or datetime.now(UTC),
        )

    def delete_reset_token(self, token: str) -> None:
        self._resets.delete_item(Key={"token": token})

    def get_by_phone(self, phone: str) -> UserRecord | None:
        key = (phone or "").strip()
        if not key:
            return None
        kwargs: dict = {
            "FilterExpression": "phone = :p AND phone_verified = :t",
            "ExpressionAttributeValues": {":p": key, ":t": True},
        }
        while True:
            response = self._users.scan(**kwargs)
            items = response.get("Items") or []
            if items:
                return self._item_to_user(items[0])
            last = response.get("LastEvaluatedKey")
            if not last:
                return None
            kwargs["ExclusiveStartKey"] = last

    def save_otp(self, record: OtpRecord) -> OtpRecord:
        ttl = int(record.created_at.timestamp()) + get_settings().otp_ttl_seconds
        self._otps.put_item(
            Item={
                "email": record.email.lower(),
                "phone": record.phone,
                "code_hash": record.code_hash,
                "purpose": record.purpose,
                "user_id": record.user_id,
                "attempts": record.attempts,
                "created_at": record.created_at.isoformat(),
                "ttl": ttl,
            }
        )
        return record

    def get_otp(self, email: str) -> OtpRecord | None:
        response = self._otps.get_item(Key={"email": email.lower()})
        item = response.get("Item")
        if not item:
            return None
        return OtpRecord(
            email=item["email"],
            phone=item.get("phone") or "",
            code_hash=item["code_hash"],
            purpose=item["purpose"],
            user_id=item.get("user_id") or "",
            attempts=int(item.get("attempts") or 0),
            created_at=_parse_dt(item.get("created_at")) or datetime.now(UTC),
        )

    def delete_otp(self, email: str) -> None:
        self._otps.delete_item(Key={"email": email.lower()})


@lru_cache(maxsize=1)
def get_user_store() -> UserStore:
    if get_settings().uses_dynamodb():
        return DynamoUserStore()
    return MemoryUserStore()
