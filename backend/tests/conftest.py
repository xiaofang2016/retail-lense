import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-must-be-32-bytes!")
os.environ.setdefault("ALLOW_SIGNUP", "true")

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.email import MemoryEmailSender, get_email_sender
from services.user_store import get_user_store


@pytest.fixture(autouse=True)
def clean_store():
    store = get_user_store()
    store.reset()
    sender = get_email_sender()
    if isinstance(sender, MemoryEmailSender):
        sender.clear()
    yield
    store.reset()
    if isinstance(sender, MemoryEmailSender):
        sender.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
