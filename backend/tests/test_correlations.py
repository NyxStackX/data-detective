from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_correlations():
    response = client.get("/investigation/correlations")

    assert response.status_code == 200

    data = response.json()

    assert data["signal"] == "correlated_investigation_lead"
    assert data["minimum_signals"] == 2
    assert data["scoring"]["concentration"] == 3
    assert data["scoring"]["repeated_transfers"] == 2
    assert data["scoring"]["night_access"] == 2
    assert data["leads_detected"] == 16

    for lead in data["leads"]:
        assert lead["signal_count"] >= 2
        assert lead["score"] > 0
        assert len(lead["signals"]) >= 2
        assert lead["entity_id"]
        assert lead["entity_name"]


def test_aurum_is_correlated():
    response = client.get("/investigation/correlations")

    assert response.status_code == 200

    data = response.json()

    matches = [
        lead
        for lead in data["leads"]
        if lead["entity_name"] == "Aurum Advisory Partners S.a r.l."
    ]

    assert len(matches) == 1

    lead = matches[0]

    assert lead["signal_count"] == 2
    assert lead["score"] == 5
    assert "concentration" in lead["signals"]
    assert "repeated_transfers" in lead["signals"]
