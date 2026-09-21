from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_financial_flows():
    response = client.get("/investigation/financial-flows")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "financial_flow_analysis"
    assert data["min_volume"] == 100000.0
    assert data["flows_detected"] > 0

    for flow in data["flows"]:
        assert flow["source_entity_id"]
        assert flow["destination_entity_id"]
        assert flow["source_entity_id"] != flow["destination_entity_id"]
        assert flow["transaction_count"] > 0
        assert flow["total_volume"] >= 100000
        assert flow["average_transaction_amount"] > 0
