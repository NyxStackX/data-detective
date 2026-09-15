from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_night_access_anomalies():
    response = client.get(
        "/investigation/anomalies/night-access"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "unusual_night_access"
    assert data["night_window"] == "00:00-05:59"
    assert data["min_night_logs"] == 10
    assert data["min_night_ratio"] == 0.05
    assert data["anomalies_detected"] == 5

    for anomaly in data["anomalies"]:
        assert anomaly["night_logs"] >= 10
        assert anomaly["night_ratio"] >= 0.05
        assert anomaly["total_logs"] >= anomaly["night_logs"]


def test_top_night_access_anomaly():
    response = client.get(
        "/investigation/anomalies/night-access"
    )

    assert response.status_code == 200

    data = response.json()

    top = data["anomalies"][0]

    assert top["employee_id"] == "EMP-0277"
    assert top["night_logs"] == 22
    assert top["total_logs"] == 168
    assert top["night_ratio"] == 0.131
