from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_entity_network():
    response = client.get("/investigation/entity-network")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "entity_network_analysis"
    assert data["nodes_count"] == 207
    assert data["edges_count"] > 0

    for node in data["nodes"]:
        assert node["entity_id"]
        assert node["entity_name"]
        assert node["entity_type"]

    for edge in data["edges"]:
        assert edge["source_entity_id"]
        assert edge["target_entity_id"]
        assert edge["source_entity_id"] != edge["target_entity_id"]
        assert edge["relation_count"] > 0
        assert "parent_subsidiary" in edge["relation_types"]
