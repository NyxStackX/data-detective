from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_people():
    response = client.get("/investigation/people")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "people_entity_analysis"
    assert data["employees_count"] == 478
    assert data["officers_count"] == 292
    assert data["people_count"] == 770

    for person in data["people"]:
        assert person["person_id"]
        assert person["name"]
        assert person["role"]
        assert person["entity_id"]
        assert person["entity_name"]
        assert person["source"] in {"employee", "company_officer"}
