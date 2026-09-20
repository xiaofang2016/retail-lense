import hashlib
import hmac

import pytest
import streamlit as st

from services import session


@pytest.fixture(autouse=True)
def _clear_streamlit_state():
    st.session_state.clear()
    yield
    st.session_state.clear()


def _raise_skip_api(_token):
    raise RuntimeError("skip api")


def test_save_login_persists_refresh_token(monkeypatch):
    captured = {}
    writes = []

    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session.api_client, "me", lambda token: {"username": "alice"})
    monkeypatch.setattr(session, "_write_browser_cookie", lambda *args, **kwargs: writes.append((args, kwargs)))
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "test-secret")

    def fake_save(session_id, access_token, user, ttl_seconds, refresh_token=None, remember_me=False):
        captured["session_id"] = session_id
        captured["access_token"] = access_token
        captured["user"] = user
        captured["ttl_seconds"] = ttl_seconds
        captured["refresh_token"] = refresh_token
        captured["remember_me"] = remember_me
        return True

    monkeypatch.setattr(session.session_store, "save", fake_save)

    session.save_login("access-123", refresh_token_value="refresh-456")

    assert captured["access_token"] == "access-123"
    assert captured["refresh_token"] == "refresh-456"
    assert captured["remember_me"] is False
    assert st.session_state["refresh_token"] == "refresh-456"
    assert st.session_state["_session_id"] == captured["session_id"]
    assert st.session_state["_pending_session_id"] == captured["session_id"]
    # Cookie write would be aborted by switch_page; prepare() does it next run.
    assert writes == []


def test_restore_loads_session_from_cookie(monkeypatch):
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_read_session_cookie", lambda: "sid-1")
    monkeypatch.setattr(
        session.session_store,
        "load",
        lambda session_id: {
            "access_token": "access-from-redis",
            "refresh_token": "refresh-from-redis",
            "user": {"username": "alice"},
            "remember_me": True,
        }
        if session_id == "sid-1"
        else None,
    )
    monkeypatch.setattr(session, "_token_has_expired", lambda token: False)
    monkeypatch.setattr(session.api_client, "me", _raise_skip_api)

    assert session.token() == "access-from-redis"
    assert st.session_state["user"]["username"] == "alice"
    assert st.session_state["remember_me"] is True
    assert st.session_state["_session_id"] == "sid-1"


def test_restore_refreshes_cached_user_from_redis(monkeypatch):
    st.session_state["access_token"] = "already-there"
    st.session_state["user"] = {"username": "alice", "is_admin": False}
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_read_session_cookie", lambda: "sid-1")
    monkeypatch.setattr(
        session.session_store,
        "load",
        lambda session_id: {
            "access_token": "access-from-redis",
            "user": {"username": "alice", "is_admin": True},
            "remember_me": True,
        }
        if session_id == "sid-1"
        else None,
    )
    monkeypatch.setattr(session, "_token_has_expired", lambda token: False)
    monkeypatch.setattr(session.api_client, "me", _raise_skip_api)

    session._restore()
    assert st.session_state["access_token"] == "already-there"
    assert st.session_state["user"]["is_admin"] is True


def test_current_user_refreshes_is_admin_from_api(monkeypatch):
    st.session_state["access_token"] = "access-123"
    st.session_state["user"] = {"username": "alice", "user_id": "u1", "is_admin": False}
    st.session_state["_session_id"] = "sid-1"
    captured = {}

    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_token_has_expired", lambda token: False)
    monkeypatch.setattr(session, "_restore", lambda: None)
    monkeypatch.setattr(
        session.api_client,
        "me",
        lambda token: {"username": "alice", "user_id": "u1", "is_admin": True},
    )
    monkeypatch.setattr(
        session.session_store,
        "load",
        lambda session_id: {
            "access_token": "access-123",
            "refresh_token": "refresh-123",
            "user": {"username": "alice", "user_id": "u1", "is_admin": False},
            "remember_me": False,
        },
    )

    def fake_save(session_id, access_token, user, ttl_seconds, refresh_token=None, remember_me=False):
        captured["user"] = user
        captured["session_id"] = session_id
        return True

    monkeypatch.setattr(session.session_store, "save", fake_save)

    user = session.current_user()
    assert user["is_admin"] is True
    assert st.session_state["user"]["is_admin"] is True
    assert captured["user"]["is_admin"] is True
    assert captured["session_id"] == "sid-1"


def test_token_refreshes_expired_access_token(monkeypatch):
    st.session_state["access_token"] = "expired-access"
    st.session_state["refresh_token"] = "refresh-123"

    monkeypatch.setattr(session, "_token_has_expired", lambda token: True)
    monkeypatch.setattr(session.session_store, "enabled", lambda: False)
    monkeypatch.setattr(
        session.api_client,
        "refresh_access_token",
        lambda refresh_token: {"access_token": "fresh-access", "refresh_token": "fresh-refresh"},
    )

    assert session.token() == "fresh-access"
    assert st.session_state["access_token"] == "fresh-access"
    assert st.session_state["refresh_token"] == "fresh-refresh"


def test_session_cookie_roundtrip_hmac(monkeypatch):
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "test-secret")
    signed = session._sign_session_id("sid-abc")
    assert signed.startswith("sid-abc.")
    assert session._unsign_session_id(signed) == "sid-abc"
    tampered = signed[:-1] + ("0" if signed[-1] != "0" else "1")
    assert session._unsign_session_id(tampered) is None
    expected = hmac.new(b"test-secret", b"sid-abc", hashlib.sha256).hexdigest()
    assert signed == f"sid-abc.{expected}"


def test_prepare_reruns_after_cookie_restore(monkeypatch):
    reruns = []
    writes = []
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setenv("SESSION_COOKIE_PASSWORD", "test-secret")
    monkeypatch.setattr(session, "_read_session_cookie", lambda: "sid-1")
    monkeypatch.setattr(session, "_write_browser_cookie", lambda *args, **kwargs: writes.append(args))
    monkeypatch.setattr(
        session.session_store,
        "load",
        lambda session_id: {
            "access_token": "access-from-redis",
            "refresh_token": "refresh-from-redis",
            "user": {"username": "alice"},
            "remember_me": False,
        }
        if session_id == "sid-1"
        else None,
    )
    monkeypatch.setattr(session, "_token_has_expired", lambda token: False)
    monkeypatch.setattr(session.api_client, "me", _raise_skip_api)
    monkeypatch.setattr(st, "rerun", lambda: reruns.append("rerun"))

    session.prepare()

    assert st.session_state["access_token"] == "access-from-redis"
    assert st.session_state["_retaillen_nav_synced"] is True
    assert reruns == ["rerun"]
    assert writes == []


def test_prepare_writes_pending_cookie_after_nav_is_synced(monkeypatch):
    writes = []
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_restore", lambda: None)
    monkeypatch.setattr(session, "_write_browser_cookie", lambda session_id, max_age=0: writes.append((session_id, max_age)))
    st.session_state["access_token"] = "tok"
    st.session_state["_retaillen_nav_synced"] = True
    st.session_state["_pending_session_id"] = "sid-new"
    st.session_state["_pending_session_ttl"] = 3600

    session.prepare()

    assert writes == [("sid-new", 3600)]
    assert "_pending_session_id" not in st.session_state


def test_prepare_preserves_pending_cookie_when_nav_rerun_is_needed(monkeypatch):
    writes = []
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_restore", lambda: None)
    monkeypatch.setattr(session, "_write_browser_cookie", lambda *args, **kwargs: writes.append(args))
    monkeypatch.setattr(st, "rerun", lambda: (_ for _ in ()).throw(RuntimeError("rerun")))
    st.session_state["access_token"] = "tok"
    st.session_state["_pending_session_id"] = "sid-new"
    st.session_state["_pending_session_ttl"] = 99

    try:
        session.prepare()
    except RuntimeError as exc:
        assert str(exc) == "rerun"

    assert writes == []
    assert st.session_state["_pending_session_id"] == "sid-new"
    assert st.session_state["_retaillen_nav_synced"] is True
