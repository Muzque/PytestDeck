from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_repo_root() -> str:
    cwd = Path.cwd().resolve()
    return str(cwd.parent if cwd.name == "backend" else cwd)


def test_api_test_detail_endpoint_pytest_function():
    repo_root = get_repo_root()
    node_id = (
        "backend/tests/integration/api/test_api_discover.py::test_api_discover_endpoint"
    )

    response = client.post(
        "/api/test-detail",
        json={"target_path": repo_root, "node_id": node_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_api_discover_endpoint"
    assert data["type"] == "function"
    assert "backend/tests/integration/api/test_api_discover.py" in data["file_path"]


def test_api_test_detail_endpoint_behave_scenario():
    repo_root = get_repo_root()
    node_id = (
        "backend/tests/acceptance/features/api_discovery.feature::"
        "Discovering tests in the backend unit test suite"
    )

    response = client.post(
        "/api/test-detail",
        json={"target_path": repo_root, "node_id": node_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Discovering tests in the backend unit test suite"
    assert data["type"] == "scenario"
    assert len(data["steps"]) >= 4


def test_api_test_detail_invalid_node():
    repo_root = get_repo_root()
    response = client.post(
        "/api/test-detail",
        json={
            "target_path": repo_root,
            "node_id": "nonexistent_dir/fake_test.py::func",
        },
    )
    assert response.status_code == 400


def test_api_test_detail_resets_on_code_modification(tmp_path, monkeypatch):
    test_db = tmp_path / "detail_test.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(test_db))

    target_repo = tmp_path / "sub_repo"
    target_repo.mkdir()
    test_file = target_repo / "test_sample.py"
    test_file.write_text("def test_calc(): pass\n", encoding="utf-8")

    from infrastructure.history_db import HistoryDatabase
    from infrastructure.test_detail_service import compute_file_hash

    f_hash = compute_file_hash(test_file)

    db = HistoryDatabase()
    db.save_run(
        "test_sample.py::test_calc",
        outcome="passed",
        duration=0.1,
        output="passed output",
        file_hash=f_hash,
    )

    # First fetch: unmodified -> latest_run should be present
    resp = client.post(
        "/api/test-detail",
        json={"target_path": str(target_repo), "node_id": "test_sample.py::test_calc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["latest_run"] is not None
    assert data["modified_since_run"] is False

    # Modify the test file
    test_file.write_text("def test_calc():\n    return 42\n", encoding="utf-8")

    # Second fetch: modified -> latest_run should be reset to None, modified_since_run is True
    resp2 = client.post(
        "/api/test-detail",
        json={"target_path": str(target_repo), "node_id": "test_sample.py::test_calc"},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["latest_run"] is None
    assert data2["modified_since_run"] is True
