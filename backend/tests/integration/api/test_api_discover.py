from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_api_discover_endpoint():
    response = client.post("/api/discover", json={
        "target_path": "/Users/xuandi/repo/PytestDeck",
        "suite_rel_path": "backend/tests/unit"
    })
    assert response.status_code == 200
    data = response.json()
    assert "tree" in data
    assert data["suite"] == "backend/tests/unit"


def test_api_discover_invalid_path():
    response = client.post("/api/discover", json={
        "target_path": "/invalid/nonexistent/path/xyz999"
    })
    assert response.status_code == 400
