import pytest

from services.secrets import _extract_secret_value


def test_extract_plain_secret():
    assert _extract_secret_value("plain-signing-key") == "plain-signing-key"


def test_extract_json_secret():
    assert _extract_secret_value('{"JWT_SECRET":"json-signing-key"}') == "json-signing-key"


def test_reject_json_without_supported_key():
    with pytest.raises(RuntimeError, match="must contain"):
        _extract_secret_value('{"other":"value"}')


def test_reject_empty_secret():
    with pytest.raises(RuntimeError, match="empty"):
        _extract_secret_value("")
