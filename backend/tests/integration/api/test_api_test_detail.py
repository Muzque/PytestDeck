from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_repo_root() -> str:
    cwd = Path.cwd().resolve()
    return str(cwd.parent if cwd.name == "backend" else cwd)


def test_api_test_detail_endpoint_pytest_function():
    repo_root = get_repo_root()
    node_id = "backend/tests/integration/api/test_api_discover.py::test_api_discover_endpoint"

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
        json={"target_path": repo_root, "node_id": "nonexistent_dir/fake_test.py::func"},
    )
    assert response.status_code == 400
