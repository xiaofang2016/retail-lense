import json
import os

from services.runtime_config import (
    _get_secret_string,
    apply,
    keys_to_fetch,
    secret_id,
    should_fetch,
)


def test_secret_id_prefixes_env_name():
    assert secret_id("AUTH_API_URL") == "retaillen/AUTH_API_URL"
    assert secret_id("SESSION_COOKIE_PASSWORD") == "retaillen/SESSION_COOKIE_PASSWORD"


def test_local_values_skip_secrets_manager(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("AUTH_API_URL", "https://local")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("REDIS_PASSWORD", "local")
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "local-cookie")
    monkeypatch.setattr(
        "services.runtime_config._get_secret_string",
        lambda name: (_ for _ in ()).throw(AssertionError("must not call Secrets Manager")),
    )
    apply.cache_clear()
    assert keys_to_fetch() == ()
    assert apply() == {}
    assert os.getenv("AUTH_API_URL") == "https://local"


def test_aws_keeps_explicit_env_values(monkeypatch):
    monkeypatch.setenv("APP_ENV", "aws")
    monkeypatch.setenv("AUTH_API_URL", "https://already-set")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("REDIS_PASSWORD", "")
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "")
    assert should_fetch("AUTH_API_URL") is False
    assert should_fetch("REDIS_URL") is True


def test_aws_empty_values_load_retaillen_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "aws")
    monkeypatch.setenv("AUTH_API_URL", "")
    monkeypatch.setenv("REDIS_URL", "")
    monkeypatch.setenv("REDIS_PASSWORD", "")
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "")
    secrets = {
        "retaillen/AUTH_API_URL": "https://example.lambda-url.us-east-1.on.aws/",
        "retaillen/REDIS_URL": "redis://:secret@10.0.1.10:6379/0",
        "retaillen/REDIS_PASSWORD": json.dumps({"REDIS_PASSWORD": "secret"}),
        "retaillen/SESSION_COOKIE_PASSWORD": "cookie-secret",
    }
    monkeypatch.setattr(
        "services.runtime_config._get_secret_string",
        lambda name: secrets[name],
    )
    apply.cache_clear()
    _get_secret_string.cache_clear()
    loaded = apply()
    assert loaded["AUTH_API_URL"] == "https://example.lambda-url.us-east-1.on.aws"
    assert loaded["REDIS_URL"] == secrets["retaillen/REDIS_URL"]
    assert loaded["REDIS_PASSWORD"] == "secret"
    assert loaded["SESSION_COOKIE_PASSWORD"] == "cookie-secret"
    assert os.getenv("AUTH_API_URL") == loaded["AUTH_API_URL"]
    assert os.getenv("SESSION_COOKIE_PASSWORD") == "cookie-secret"
