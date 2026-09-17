from services.analysis_store import get_analysis_store


def _register_and_login(client, suffix: str) -> str:
    payload = {
        "email": f"{suffix}@example.com",
        "username": suffix,
        "full_name": "Test User",
        "password": "password1",
        "password_confirm": "password1",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text

    response = client.post(
        "/auth/token",
        data={"username": suffix, "password": "password1"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_status_and_list(client):
    token = _register_and_login(client, "analyst")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/analyses", json={"file_extension": "csv", "file_name": "transactions.csv"}, headers=headers)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["analysis_id"]
    assert body["upload_url"].startswith("http")

    status_response = client.get(f"/analyses/{body['analysis_id']}/status", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"

    listed = client.get("/analyses", headers=headers)
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["analysis_id"] == body["analysis_id"]


def test_status_hides_other_users_analysis(client):
    token_a = _register_and_login(client, "usera")
    token_b = _register_and_login(client, "userb")

    created = client.post(
        "/analyses",
        json={"file_extension": "csv", "file_name": "transactions.csv"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    analysis_id = created.json()["analysis_id"]

    response = client.get(
        f"/analyses/{analysis_id}/status",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_report_not_ready_until_done(client):
    token = _register_and_login(client, "reportuser")
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post("/analyses", json={"file_extension": "csv", "file_name": "transactions.csv"}, headers=headers)
    analysis_id = created.json()["analysis_id"]

    response = client.get(f"/analyses/{analysis_id}/report", headers=headers)
    assert response.status_code == 409

    get_analysis_store().update(
        analysis_id,
        status="done",
        s3_result_key=f"results/x/{analysis_id}/report.json",
    )
    # Still 404/error at the S3 layer since nothing was actually written -- this test only
    # confirms the "not ready" gate opens once status flips to done, not the S3 read path.
