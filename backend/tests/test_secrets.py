import pytest

from core.settings import get_settings
from services.secrets import _extract_secret_value


def test_extract_plain_secret():
    assert _extract_secret_value("plain-signing-key") == "plain-signing-key"


def test_extract_json_secret():
    assert _extract_secret_value('{"JWT_SECRET":"json-signing-key"}') == "json-signing-key"


def test_extract_json_field():
    assert _extract_secret_value('{"SMTP_USER":"mailer"}', field="SMTP_USER") == "mailer"
    assert (
        _extract_secret_value('{"SMTP_PASSWORD":"s3cret"}', field="SMTP_PASSWORD")
        == "s3cret"
    )


def test_reject_json_without_supported_key():
    with pytest.raises(RuntimeError, match="must contain"):
        _extract_secret_value('{"other":"value"}')


def test_reject_empty_secret():
    with pytest.raises(RuntimeError, match="empty"):
        _extract_secret_value("")


def test_aws_loads_smtp_secrets_when_empty(monkeypatch):
    def fake_get_secret(name, field=None):
        secrets = {
            "retaillen/jwt": "jwt-from-sm",
            "retaillen/SMTP_USER": "ses-user",
            "retaillen/SMTP_PASSWORD": "ses-pass",
        }
        return secrets[name]

    monkeypatch.setenv("APP_ENV", "aws")
    monkeypatch.setenv("JWT_SECRET_NAME", "retaillen/jwt")
    monkeypatch.setenv("SMTP_HOST", "email-smtp.us-east-1.amazonaws.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@example.com")
    monkeypatch.setenv("SMTP_AUTH_STRATEGY", "TLS")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setattr("services.secrets.get_secret", fake_get_secret)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.smtp_user == "ses-user"
        assert settings.smtp_password == "ses-pass"
    finally:
        get_settings.cache_clear()


def test_mailpit_skips_smtp_secrets(monkeypatch):
    def fake_get_secret(name, field=None):
        if name == "retaillen/jwt":
            return "jwt-from-sm"
        raise AssertionError(f"unexpected secret {name}")

    monkeypatch.setenv("APP_ENV", "aws")
    monkeypatch.setenv("JWT_SECRET_NAME", "retaillen/jwt")
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "noreply@retaillen.local")
    monkeypatch.setenv("SMTP_AUTH_STRATEGY", "NONE")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_PASSWORD", "")
    monkeypatch.setattr("services.secrets.get_secret", fake_get_secret)
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.smtp_user == ""
        assert settings.smtp_password == ""
    finally:
        get_settings.cache_clear()
