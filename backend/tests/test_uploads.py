def test_transactions_sample_falls_back_locally(client):
    response = client.get("/uploads/transactions-sample")
    assert response.status_code == 200
    assert "InvoiceNo" in response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-sample-source"] == "local"
