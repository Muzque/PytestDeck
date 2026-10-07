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
    # Setup test file in tmp_path
    target_repo = tmp_path / "repo"
    target_repo.mkdir()
    test_file = target_repo / "test_one.py"
    test_file.write_text("def test_run(): pass\n", encoding="utf-8")

    from infrastructure.test_detail_service import compute_file_hash

    f_hash = compute_file_hash(test_file)

    target_param = f"target_path={target_repo}"

    # Check initially empty
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert resp.json() == {"runs": {}}

    # Seed run via HistoryDatabase
    db = HistoryDatabase()
    db.save_run(
        "test_one.py::test_run",
        outcome="passed",
        output="Sample terminal output",
        code_hash="hash1",
        file_hash=f_hash,
    )

    # Fetch all
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert "test_one.py::test_run" in runs
    assert runs["test_one.py::test_run"]["outcome"] == "passed"

    # Fetch single
    resp = client.get(f"/api/test-runs?{target_param}&node_id=test_one.py::test_run")
    assert resp.status_code == 200
    assert resp.json()["run"]["code_hash"] == "hash1"

    # Prune
    resp = client.post(
        "/api/test-runs/prune",
        json={"target_path": str(target_repo), "valid_nodes": ["other.py::test"]},
    )
    assert resp.status_code == 200
    assert resp.json()["pruned_count"] == 1

    # Verify pruned
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.json() == {"runs": {}}


def test_api_history_file_modified_reset(client, tmp_path):
    target_repo = tmp_path / "my_project"
    target_repo.mkdir()
    test_file = target_repo / "test_math.py"
    test_file.write_text("def test_add(): pass\n", encoding="utf-8")

    from infrastructure.test_detail_service import compute_file_hash

    initial_hash = compute_file_hash(test_file)

    target_param = f"target_path={target_repo}"

    db = HistoryDatabase()
    db.save_run(
        "test_math.py::test_add",
        outcome="passed",
        duration=0.08,
        output="1 passed",
        file_hash=initial_hash,
    )

    # Verify initial run is returned
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert "test_math.py::test_add" in resp.json()["runs"]

    # Modify file content (simulating code edit by developer)
    test_file.write_text("def test_add():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    assert compute_file_hash(test_file) != initial_hash

    # Now GET /api/test-runs should detect file hash change and reset result
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert resp.json()["runs"] == {}

    # Verify single node lookup also returns None
    resp_single = client.get(
        f"/api/test-runs?{target_param}&node_id=test_math.py::test_add"
    )
    assert resp_single.status_code == 200
    assert resp_single.json()["run"] is None


def test_api_run_options_endpoints(client):
    # Check default run options
    resp = client.get("/api/run-options")
    assert resp.status_code == 200
    assert resp.json() == {"marker_filter": "", "extra_args": ""}

    # Save run options
    post_resp = client.post(
        "/api/run-options",
        json={"marker_filter": "unit and not slow", "extra_args": "-s --tb=short"},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # Retrieve saved run options
    get_resp = client.get("/api/run-options")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["marker_filter"] == "unit and not slow"
    assert data["extra_args"] == "-s --tb=short"
