from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_timeline():
    response = client.get("/investigation/timeline")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "investigation_timeline"
    assert data["min_amount"] == 500000.0
    assert data["events_count"] == 100

    for event in data["events"]:
        assert event["amount"] >= 500000
        assert event["source_entity_id"]
        assert event["destination_entity_id"]
        assert event["transaction_id"]
