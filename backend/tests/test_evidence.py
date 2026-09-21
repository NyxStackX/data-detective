from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_evidence():
    response = client.get("/investigation/evidence")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "investigation_evidence"
    assert data["evidence_count"] == 50

    for evidence in data["evidence"]:
        assert evidence["evidence_id"]
        assert evidence["type"] == "large_transaction"
        assert evidence["transaction_id"]
        assert evidence["source_entity_id"]
        assert evidence["destination_entity_id"]
        assert evidence["source_entity_id"] != evidence["destination_entity_id"]
        assert evidence["amount"] > 0
