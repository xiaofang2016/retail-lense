import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-must-be-32-bytes!")
os.environ.setdefault("ALLOW_SIGNUP", "true")

import pytest
from fastapi.testclient import TestClient

from api.main import app
from services.analysis_store import get_analysis_store
from services.email import MemoryEmailSender, get_email_sender
from services.sns import MemorySnsSender, get_sns_sender
from services.user_store import get_user_store


@pytest.fixture(autouse=True)
def clean_store():
    store = get_user_store()
    store.reset()
    analyses = get_analysis_store()
    analyses.reset()
    sender = get_email_sender()
    if isinstance(sender, MemoryEmailSender):
        sender.clear()
    sms = get_sns_sender()
    if isinstance(sms, MemorySnsSender):
        sms.clear()
    yield
    store.reset()
    analyses.reset()
    if isinstance(sender, MemoryEmailSender):
        sender.clear()
    if isinstance(sms, MemorySnsSender):
        sms.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
