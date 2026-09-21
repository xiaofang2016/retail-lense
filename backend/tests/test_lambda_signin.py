import json

from lambda_signin.handler import lambda_handler

from tests.test_auth import _register


def _event(
    body: dict,
    path: str = "/auth/signin",
    ip: str = "200.0.113.10",
    user_agent: str = "pytest",
) -> dict:
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": "POST", "sourceIp": ip}},
        "headers": {"user-agent": user_agent},
        "body": json.dumps(body),
    }


def test_lambda_signin_success(client):
    payload, _ = _register(client, "lamok")
    response = lambda_handler(
        _event({"username": payload["username"], "password": payload["password"]}),
        None,
    )
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    history = client.get(
        "/auth/login-history",
        headers={"Authorization": f"Bearer {body['access_token']}"},
        params={"limit": 10},
    )
    assert history.status_code == 200
    items = history.json()["items"]
    assert items
    assert items[0]["success"] is True
    assert items[0]["ip"] == "200.0.113.10"


def test_lambda_signin_wrong_password(client):
    payload, _ = _register(client, "lambad")
    response = lambda_handler(
        _event({"username": payload["username"], "password": "wrong-pass"}),
        None,
    )
    assert response["statusCode"] == 401
    assert json.loads(response["body"])["detail"] == "Incorrect username or password"

    login = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
    )
    token = login.json()["access_token"]
    history = client.get("/auth/login-history", headers={"Authorization": f"Bearer {token}"})
    assert any(not item["success"] for item in history.json()["items"])


def test_lambda_signin_bad_body():
    response = lambda_handler({"rawPath": "/auth/signin", "body": "not-json"}, None)
    assert response["statusCode"] == 400


def test_lambda_register_success(client):
    response = lambda_handler(
        _event(
            {
                "email": "lambda-reg@example.com",
                "username": "lambdareg",
                "full_name": "Lambda Reg",
                "password": "password1",
                "password_confirm": "password1",
            },
            path="/auth/register",
        ),
        None,
    )
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["username"] == "lambdareg"
    assert body["email"] == "lambda-reg@example.com"


def test_lambda_register_conflict(client):
    _register(client, "lamdup")
    response = lambda_handler(
        _event(
            {
                "email": "other@example.com",
                "username": "lamdup",
                "full_name": "Dup",
                "password": "password1",
                "password_confirm": "password1",
            },
            path="/auth/register",
        ),
        None,
    )
    assert response["statusCode"] == 409


def test_lambda_unknown_path():
    response = lambda_handler(_event({}, path="/unknown"), None)
    assert response["statusCode"] == 404


def test_lambda_signin_prefers_x_forwarded_for(client):
    payload, _ = _register(client, "lamxff")
    event = _event({"username": payload["username"], "password": payload["password"]}, ip="10.0.1.4")
    event["headers"]["x-forwarded-for"] = "198.51.100.20, 10.0.1.4"
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    history = client.get(
        "/auth/login-history",
        headers={"Authorization": f"Bearer {body['access_token']}"},
        params={"limit": 1},
    )
    assert history.json()["items"][0]["ip"] == "198.51.100.20"
