from datetime import UTC, datetime
from uuid import uuid4

from core.exceptions import RegistrationConflict
from core.security.hasher import get_hasher
from schema.auth import CreateUserRegistration
from schema.user import UserOut, UserRecord
from services.user_store import UserStore, get_user_store


class RegistrationService:
    def __init__(self, store: UserStore | None = None) -> None:
        self.store = store or get_user_store()

    def register_user(self, data: CreateUserRegistration) -> UserOut:
        if self.store.get_by_username(data.username):
            raise RegistrationConflict("username already exists")
        if self.store.get_by_email(data.email):
            raise RegistrationConflict("email already exists")

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
        return UserOut.from_record(created)
