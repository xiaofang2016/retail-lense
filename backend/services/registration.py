from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from core.security.hasher import get_hasher
from schema.auth import CreateUserRegistration
from schema.user import UserOut, UserRecord
from services.user_store import UserStore, get_user_store


class RegistrationService:
    def __init__(self, store: UserStore | None = None) -> None:
        self.store = store or get_user_store()

    def register_user(self, data: CreateUserRegistration) -> UserOut:
        if self.store.get_by_username(data.username):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="username already exists")
        if self.store.get_by_email(data.email):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="email already exists")

        user = UserRecord(
            user_id=str(uuid4()),
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            password_hash=get_hasher().hash(data.password),
            login_attempts=0,
            locked_at=None,
            created_at=datetime.now(UTC),
        )
        created = self.store.create(user)
        return UserOut(
            user_id=created.user_id,
            email=created.email,
            username=created.username,
            full_name=created.full_name,
            created_at=created.created_at,
        )
