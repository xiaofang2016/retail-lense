from datetime import UTC, datetime, timedelta

from services.email import MemoryEmailSender, get_email_sender
from services.password_reset import PasswordResetService
from services.user_store import get_user_store


def _register(client, suffix: str = "resetme"):
    payload = {
        "email": f"{suffix}@example.com",
        "username": suffix,
        "full_name": "Reset User",
        "password": "password1",
        "password_confirm": "password1",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return payload


def test_forgot_password_unknown_email_is_ok(client):
    response = client.post("/users/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert get_user_store().get_reset_token("unused") is None


def test_forgot_and_reset_password(client):
    payload = _register(client)
    sender = get_email_sender()
    assert isinstance(sender, MemoryEmailSender)
    sender.clear()

    response = client.post("/users/forgot-password", json={"email": payload["email"].upper()})
    assert response.status_code == 200
    assert len(sender.outbox) == 1
    assert payload["email"] in sender.outbox[0].to
    html = sender.outbox[0].html
    assert "/Reset_Password?token=" in html
    assert "/reset-password/" not in html
    token = html.split("token=")[1].split('"')[0]

    new_password = "password2xyz"
    reset = client.post(
        "/users/reset-password",
        json={
            "token": token,
            "email": payload["email"],
            "password": new_password,
            "passwordConfirm": new_password,
        },
    )
    assert reset.status_code == 200

    old = client.post("/auth/token", data={"username": payload["username"], "password": payload["password"]})
    assert old.status_code == 401

    fresh = client.post("/auth/token", data={"username": payload["username"], "password": new_password})
    assert fresh.status_code == 200

    reused = client.post(
        "/users/reset-password",
        json={
            "token": token,
            "email": payload["email"],
            "password": "password3xyz",
            "passwordConfirm": "password3xyz",
        },
    )
    assert reused.status_code == 400


def test_reset_password_mismatch(client):
    response = client.post(
        "/users/reset-password",
        json={
            "token": "abc",
            "email": "a@example.com",
            "password": "password1",
            "passwordConfirm": "password2",
        },
    )
    assert response.status_code == 422


def test_expired_reset_token(client):
    payload = _register(client, "expire")
    service = PasswordResetService()
    record = service.generate_reset_token(payload["email"])
    assert record is not None
    record.created_at = datetime.now(UTC) - timedelta(hours=49)
    get_user_store().save_reset_token(record)

    response = client.post(
        "/users/reset-password",
        json={
            "token": record.token,
            "email": payload["email"],
            "password": "password9xyz",
            "passwordConfirm": "password9xyz",
        },
    )
    assert response.status_code == 400
