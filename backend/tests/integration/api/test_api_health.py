from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PytestDeck"
    assert "environment" in data
    assert data["environment"]["ready"] is True


def test_api_health_ready_when_ready(monkeypatch):
    monkeypatch.delenv("PYTESTDECK_ENV_STATUS_FILE", raising=False)
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["environment"]["ready"] is True


def test_api_health_ready_when_preparing(monkeypatch, tmp_path):
    status_file = tmp_path / "env_status"
    status_file.write_text("running\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status_file))

    response = client.get("/api/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "running"
    assert data["environment"]["ready"] is False


def test_api_health_logs(monkeypatch, tmp_path):
    status_file = tmp_path / "env_status"
    status_file.write_text("running\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status_file))

    log_file = tmp_path / "env_sync.log"
    log_file.write_text("Resolved 10 packages\nInstalled 10 packages\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_SYNC_LOG", str(log_file))

    # Test /api/health/logs
    res = client.get("/api/health/logs")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert "Installed 10 packages" in data["logs"]

    # Test /api/health includes recent_logs when running
    health_res = client.get("/api/health")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert "recent_logs" in health_data["environment"]
    assert "Resolved 10 packages" in health_data["environment"]["recent_logs"]


