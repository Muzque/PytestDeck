import pytest
from fastapi.testclient import TestClient
from app import app
from infrastructure.history_db import HistoryDatabase


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "api_test.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(test_db))
    return TestClient(app)


def test_api_history_endpoints(client, tmp_path):
    # Check initially empty
    resp = client.get("/api/test-runs")
    assert resp.status_code == 200
    assert resp.json() == {"runs": {}}

    # Seed run via HistoryDatabase
    db = HistoryDatabase()
    db.save_run("test_one.py::test_run", outcome="passed", output="Sample terminal output", code_hash="hash1")

    # Fetch all
    resp = client.get("/api/test-runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert "test_one.py::test_run" in runs
    assert runs["test_one.py::test_run"]["outcome"] == "passed"

    # Fetch single
    resp = client.get("/api/test-runs?node_id=test_one.py::test_run")
    assert resp.status_code == 200
    assert resp.json()["run"]["code_hash"] == "hash1"

    # Prune
    resp = client.post("/api/test-runs/prune", json={"valid_nodes": ["other.py::test"]})
    assert resp.status_code == 200
    assert resp.json()["pruned_count"] == 1

    # Verify pruned
    resp = client.get("/api/test-runs")
    assert resp.json() == {"runs": {}}
