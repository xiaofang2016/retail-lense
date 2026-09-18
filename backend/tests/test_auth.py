from core.settings import get_settings
from services.user_store import get_user_store


def _make_admin(username: str) -> None:
    store = get_user_store()
    user = store.get_by_username(username)
    assert user is not None
    user.is_admin = True
    store.update(user)


def _register(client, suffix: str = "one"):
    payload = {
        "email": f"{suffix}@example.com",
        "username": suffix,
        "full_name": "Test User",
        "password": "password1",
        "password_confirm": "password1",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload, response.json()


def test_register_and_login(client):
    payload, user = _register(client)
    assert user["username"] == "one"
    assert "password" not in user
    assert "group" not in user

    response = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]


def test_register_conflict(client):
    _register(client, "dup")
    again = client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "username": "dup",
            "full_name": "Other",
            "password": "password1",
            "password_confirm": "password1",
        },
    )
    assert again.status_code == 409


def test_password_mismatch(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "a@example.com",
            "username": "alice",
            "full_name": "Alice",
            "password": "password1",
            "password_confirm": "password2",
        },
    )
    assert response.status_code == 422


def test_failed_login_and_history(client):
    payload, _ = _register(client, "hist")
    bad = client.post("/auth/token", data={"username": payload["username"], "password": "wrong-pass"})
    assert bad.status_code == 401

    good = client.post("/auth/token", data={"username": payload["username"], "password": payload["password"]})
    token = good.json()["access_token"]
    history = client.get("/auth/login-history", headers={"Authorization": f"Bearer {token}"})
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) == 2
    assert items[0]["success"] is True
    assert items[1]["success"] is False
    assert items[0]["ip"]


def test_lockout_after_max_attempts(client):
    payload, _ = _register(client, "lock")
    settings = get_settings()
    for _ in range(settings.security_max_login_attempts):
        response = client.post("/auth/token", data={"username": payload["username"], "password": "bad"})
        assert response.status_code == 401

    locked = client.post("/auth/token", data={"username": payload["username"], "password": payload["password"]})
    assert locked.status_code == 423


def test_ip_restriction(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "security_max_failed_per_ip", 3)
    headers = {"X-Forwarded-For": "203.0.113.50"}
    for index in range(3):
        response = client.post(
            "/auth/token",
            data={"username": f"missing{index}@example.com", "password": "nope"},
            headers=headers,
        )
        assert response.status_code == 401

    blocked = client.post(
        "/auth/token",
        data={"username": "missing-final@example.com", "password": "nope"},
        headers=headers,
    )
    assert blocked.status_code == 429


def test_non_admin_cannot_manage_blocked_ips(client):
    payload, _ = _register(client, "notadmin")
    login = client.post("/auth/token", data={"username": payload["username"], "password": payload["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    listed = client.get("/auth/blocked-ips", headers=headers)
    assert listed.status_code == 403

    blocked = client.post("/auth/blocked-ips", json={"ip": "203.0.113.9"}, headers=headers)
    assert blocked.status_code == 403


def test_user_can_block_an_ip(client):
    payload, _ = _register(client, "blockip")
    _make_admin(payload["username"])
    login = client.post("/auth/token", data={"username": payload["username"], "password": payload["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bad = client.post("/auth/blocked-ips", json={"ip": "not-an-ip"}, headers=headers)
    assert bad.status_code == 400

    blocked = client.post("/auth/blocked-ips", json={"ip": "203.0.113.9"}, headers=headers)
    assert blocked.status_code == 200
    assert blocked.json()["items"][0]["ip"] == "203.0.113.9"

    listed = client.get("/auth/blocked-ips", headers=headers)
    assert listed.json()["items"][0]["ip"] == "203.0.113.9"

    denied = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert denied.status_code == 403

    allowed = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"X-Forwarded-For": "198.51.100.10"},
    )
    assert allowed.status_code == 200

    client.request("DELETE", "/auth/blocked-ips", json={"ip": "203.0.113.9"}, headers=headers)
    again = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert again.status_code == 200
