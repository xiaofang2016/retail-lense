from lambda_signin.handler import lambda_handler
from services.sns import MemorySnsSender, get_sns_sender

from tests.test_auth import _register


PHONE = "+64211234567"


def _login(client, payload):
    return client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
    )


def _enable_2fa(client, payload, phone: str = PHONE):
    login = _login(client, payload)
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    start = client.post("/auth/2fa/phone", json={"phone": phone}, headers=headers)
    assert start.status_code == 200, start.text
    sender = get_sns_sender()
    assert isinstance(sender, MemorySnsSender)
    code = sender.outbox[-1].code
    confirm = client.post("/auth/2fa/confirm", json={"code": code}, headers=headers)
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["two_factor_enabled"] is True
    assert body["phone_hint"]
    assert PHONE not in str(body)
    return headers, sender


def test_bind_phone_then_login_requires_otp(client):
    payload, _ = _register(client, "tfauser")
    _enable_2fa(client, payload)
    sender = get_sns_sender()
    assert isinstance(sender, MemorySnsSender)

    again = _login(client, payload)
    assert again.status_code == 200
    body = again.json()
    assert body["status"] == "otp_required"
    assert "access_token" not in body
    code = sender.outbox[-1].code

    verified = client.post(
        "/auth/verify-otp",
        json={"username": payload["username"], "code": code},
    )
    assert verified.status_code == 200, verified.text
    token = verified.json()["access_token"]
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["two_factor_enabled"] is True


def test_disable_2fa_returns_to_password_login(client):
    payload, _ = _register(client, "tfadisable")
    headers, _sender = _enable_2fa(client, payload)
    disabled = client.post("/auth/2fa/disable", headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["two_factor_enabled"] is False

    login = _login(client, payload)
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_wrong_otp_rejected(client):
    payload, _ = _register(client, "tfabad")
    _enable_2fa(client, payload)
    again = _login(client, payload)
    assert again.json()["status"] == "otp_required"
    bad = client.post(
        "/auth/verify-otp",
        json={"username": payload["username"], "code": "000000"},
    )
    assert bad.status_code == 400


def test_phone_already_in_use(client):
    first, _ = _register(client, "tfaphone1")
    _enable_2fa(client, first)
    second, _ = _register(client, "tfaphone2")
    login = _login(client, second)
    token = login.json()["access_token"]
    taken = client.post(
        "/auth/2fa/phone",
        json={"phone": PHONE},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert taken.status_code == 409


def test_lambda_signin_otp_required(client):
    payload, _ = _register(client, "tfalam")
    _enable_2fa(client, payload)
    response = lambda_handler(
        {
            "rawPath": "/auth/signin",
            "requestContext": {"http": {"method": "POST", "sourceIp": "203.0.113.10"}},
            "headers": {"user-agent": "pytest"},
            "body": '{"username":"tfalam","password":"password1"}',
        },
        None,
    )
    assert response["statusCode"] == 200
    import json

    body = json.loads(response["body"])
    assert body["status"] == "otp_required"
    assert "access_token" not in body
