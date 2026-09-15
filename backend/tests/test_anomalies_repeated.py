from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_repeated_transfer_anomalies():
    response = client.get(
        "/investigation/anomalies/repeated-transfers"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "repeated_counterparty_transfers"
    assert data["min_transactions"] == 10
    assert data["min_volume"] == 1000000.0
    assert data["anomalies_detected"] > 0

    for anomaly in data["anomalies"]:
        assert anomaly["transaction_count"] >= 10
        assert anomaly["total_volume"] >= 1000000
        assert anomaly["average_transaction_amount"] > 0
        assert anomaly["source_entity_id"] != anomaly["counterparty_id"]


def test_aurum_helvetia_repeated_transfer():
    response = client.get(
        "/investigation/anomalies/repeated-transfers"
    )

    assert response.status_code == 200

    data = response.json()

    matches = [
        anomaly
        for anomaly in data["anomalies"]
        if (
            anomaly["source_entity_name"]
            == "Aurum Advisory Partners S.a r.l."
            and anomaly["counterparty_name"]
            == "Helvetia Trade Solutions AG"
        )
    ]

    assert len(matches) == 1

    anomaly = matches[0]

    assert anomaly["transaction_count"] == 14
    assert anomaly["total_volume"] == 13499999.98
    assert anomaly["average_transaction_amount"] == 964285.71
