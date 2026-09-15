from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_concentration_anomalies():
    response = client.get(
        "/investigation/anomalies/concentration"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "counterparty_concentration"
    assert data["threshold"] == 0.75
    assert data["min_volume"] == 100000.0
    assert data["anomalies_detected"] == 12

    for anomaly in data["anomalies"]:
        assert anomaly["concentration"] >= 0.75
        assert anomaly["total_flow"] >= 100000
        assert anomaly["transaction_count"] > 0
