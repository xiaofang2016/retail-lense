import os

from core.aws import drop_blank_aws_profile, session


def test_drop_blank_aws_profile(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "  ")
    monkeypatch.setenv("AWS_DEFAULT_PROFILE", "")
    drop_blank_aws_profile()
    assert "AWS_PROFILE" not in os.environ
    assert "AWS_DEFAULT_PROFILE" not in os.environ


def test_session_ignores_blank_profile(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
    sess = session()
    assert sess.profile_name in {None, "default"}
    assert "AWS_PROFILE" not in os.environ


def test_session_falls_back_when_profile_missing(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "does-not-exist-retaillen")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_PROFILE", raising=False)
    sess = session()
    assert sess.profile_name in {None, "default"}
    assert "AWS_PROFILE" not in os.environ
