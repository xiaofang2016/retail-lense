import streamlit as st

from services import session


def setup_function():
    st.session_state.clear()


def _raise_skip_api(_token):
    raise RuntimeError("skip api")


class Cookies(dict):
    def __init__(self, *args, ready=True, **kwargs):
        super().__init__(*args, **kwargs)
        self._ready = ready
        self.save_calls = 0

    def ready(self):
        return self._ready

    def save(self):
        self.save_calls += 1


def test_save_login_persists_refresh_token(monkeypatch):
    captured = {}
    cookies = Cookies()

    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session.api_client, "me", lambda token: {"username": "alice"})
    monkeypatch.setattr(session, "_cookies", lambda: cookies)

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
    assert cookies[session.SESSION_COOKIE] == captured["session_id"]
    assert st.session_state["_pending_session_id"] == captured["session_id"]
    # save() would be aborted by switch_page; the next CookieManager run writes the queue.
    assert cookies.save_calls == 0


def test_restore_loads_session_from_cookie(monkeypatch):
    cookies = Cookies({session.SESSION_COOKIE: "sid-1"})
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_cookies", lambda: cookies)
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


def test_restore_refreshes_cached_user_from_redis(monkeypatch):
    st.session_state["access_token"] = "already-there"
    st.session_state["user"] = {"username": "alice", "is_admin": False}
    cookies = Cookies({session.SESSION_COOKIE: "sid-1"})
    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_cookies", lambda: cookies)
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
    captured = {}

    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_token_has_expired", lambda token: False)
    monkeypatch.setattr(session, "_restore", lambda: None)
    monkeypatch.setattr(
        session.api_client,
        "me",
        lambda token: {"username": "alice", "user_id": "u1", "is_admin": True},
    )

    cookies = Cookies({session.SESSION_COOKIE: "sid-1"})
    monkeypatch.setattr(session, "_cookies", lambda: cookies)
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


class _CookieRunCtx:
    def __init__(self):
        self.widget_user_keys_this_run = set()


class _SharedCookieRunCtx:
    def __init__(self):
        self.shared = _CookieRunCtx()


def _install_fake_cookie_manager(monkeypatch, ctx=None):
    created = []
    ctx = ctx or _CookieRunCtx()

    def _keys():
        keys = getattr(ctx, "widget_user_keys_this_run", None)
        if keys is not None:
            return keys
        return ctx.shared.widget_user_keys_this_run

    class FakeManager(dict):
        def __init__(self):
            super().__init__()
            created.append(self)
            _keys().add(session.COOKIE_COMPONENT_KEY)

        def ready(self):
            return True

    monkeypatch.setattr(session.session_store, "enabled", lambda: True)
    monkeypatch.setattr(session, "_new_cookie_manager", FakeManager)
    monkeypatch.setattr(session, "_script_run_ctx", lambda: ctx)
    return created, ctx


def test_cookie_manager_constructed_once_when_signed_in_then_prepare(monkeypatch):
    created, _ctx = _install_fake_cookie_manager(monkeypatch)

    assert session.signed_in() is False
    session.prepare()
    session.prepare()

    assert len(created) == 1
    assert st.session_state[session.COOKIE_MANAGER_STATE_KEY] is created[0]


def test_cookie_manager_constructed_once_for_main_then_page_prepare(monkeypatch):
    created, _ctx = _install_fake_cookie_manager(monkeypatch)

    session.prepare(remount=True)
    assert session.signed_in() is False
    session.prepare()

    assert len(created) == 1


def test_cookie_manager_reconstructed_on_new_script_run(monkeypatch):
    created, ctx = _install_fake_cookie_manager(monkeypatch)

    session.prepare(remount=True)
    assert len(created) == 1

    ctx.widget_user_keys_this_run.clear()
    session.prepare(remount=True)

    assert len(created) == 2
    assert st.session_state[session.COOKIE_MANAGER_STATE_KEY] is created[1]


def test_cookie_manager_uses_shared_widget_keys(monkeypatch):
    created, ctx = _install_fake_cookie_manager(monkeypatch, ctx=_SharedCookieRunCtx())

    session.prepare(remount=True)
    session.prepare()
    assert len(created) == 1

    ctx.shared.widget_user_keys_this_run.clear()
    session.prepare(remount=True)
    assert len(created) == 2
