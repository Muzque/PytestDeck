from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_api_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "config" in response.json()
