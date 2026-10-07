from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_sample_target_repo() -> str:
    cwd = Path.cwd().resolve()
    root = cwd.parent if cwd.name == "backend" else cwd
    return str(root / "sample-target-repo")


def test_api_test_detail_endpoint_pytest_function():
    target_repo = get_sample_target_repo()
    node_id = "tests/unit/test_calculator.py::test_add"

    response = client.post(
        "/api/test-detail",
        json={"target_path": target_repo, "node_id": node_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_add"
    assert data["type"] == "function"
    assert "tests/unit/test_calculator.py" in data["file_path"]


def test_api_test_detail_endpoint_behave_scenario():
    target_repo = get_sample_target_repo()
    node_id = (
        "tests/acceptance/features/calculator.feature::"
        "Addition of two numbers"
    )

    response = client.post(
        "/api/test-detail",
        json={"target_path": target_repo, "node_id": node_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Addition of two numbers"
    assert data["type"] == "scenario"
    assert len(data["steps"]) >= 3


def test_api_test_detail_invalid_node():
    repo_root = get_sample_target_repo()
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
