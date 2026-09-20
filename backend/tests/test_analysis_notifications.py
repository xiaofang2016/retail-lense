from unittest.mock import MagicMock, patch
from uuid import UUID

from services.sns import memory_subscriptions
from services.user_store import get_user_store
from tests.test_auth import _register


def _login_headers(client, payload):
    login = client.post(
        "/auth/token",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_subscribe_and_unsubscribe_account_email(client):
    payload, user = _register(client, "notifyme")
    headers = _login_headers(client, payload)

    me = client.get("/users/me", headers=headers)
    assert me.json()["notify_email"] is False

    enabled = client.put("/users/me/analysis-notifications", json={"email": True}, headers=headers)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["notify_email"] is True
    assert "sns_email_subscription_arn" not in enabled.json()

    subs = memory_subscriptions()
    assert len(subs) == 1
    assert subs[0].endpoint == payload["email"]
    assert subs[0].user_id == user["user_id"]
    stored = get_user_store().get_by_id(user["user_id"])
    assert stored is not None
    assert stored.sns_email_subscription_arn == subs[0].arn
    UUID(subs[0].arn.rsplit(":", 1)[-1])

    again = client.put("/users/me/analysis-notifications", json={"email": True}, headers=headers)
    assert again.status_code == 200
    assert len(memory_subscriptions()) == 1

    disabled = client.put("/users/me/analysis-notifications", json={"email": False}, headers=headers)
    assert disabled.status_code == 200
    assert disabled.json()["notify_email"] is False
    assert memory_subscriptions() == []
    stored = get_user_store().get_by_id(user["user_id"])
    assert stored is not None
    assert stored.sns_email_subscription_arn == ""


def test_analysis_notifications_requires_auth(client):
    response = client.put("/users/me/analysis-notifications", json={"email": True})
    assert response.status_code == 401


def test_completion_lambda_publishes_user_id_attribute(monkeypatch):
    import importlib.util
    from pathlib import Path

    handler_path = Path(__file__).resolve().parents[1] / "lambda" / "analysis_processor" / "handler.py"
    spec = importlib.util.spec_from_file_location("analysis_complete_handler", handler_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TOPIC_ARN", "arn:aws:sns:us-east-1:1:retaillen-analysis-complete")

    table = MagicMock()
    sns = MagicMock()
    with (
        patch.object(module, "_dynamodb_table", return_value=table),
        patch.object(module.boto3, "client", return_value=sns),
    ):
        result = module.handler(
            {"Records": [{"s3": {"object": {"key": "results/user-1/analysis-9/report.json"}}}]}
        )

    assert result == {"status": "ok"}
    table.update_item.assert_called_once()
    kwargs = sns.publish.call_args.kwargs
    assert kwargs["MessageAttributes"]["user_id"]["StringValue"] == "user-1"
    assert kwargs["MessageAttributes"]["analysis_id"]["StringValue"] == "analysis-9"
    assert "analysis-9" in kwargs["Message"]
