def test_transactions_sample_falls_back_locally(client, tmp_path, monkeypatch):
    sample = tmp_path / "transactions_sample.csv"
    sample.write_text(
        "InvoiceNo,StockCode,Description,Quantity,InvoiceDate,UnitPrice,CustomerID,Country\n"
        "536365,85123A,WHITE HANGING HEART T-LIGHT HOLDER,6,2010-12-01 08:26:00,2.55,17850,United Kingdom\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("services.s3._LOCAL_SAMPLE_CANDIDATES", (sample,))

    response = client.get("/uploads/transactions-sample")
    assert response.status_code == 200
    assert "InvoiceNo" in response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-sample-source"] == "local"