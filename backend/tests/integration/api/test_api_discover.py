from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_sample_target_repo() -> str:
    cwd = Path.cwd().resolve()
    root = cwd.parent if cwd.name == "backend" else cwd
    return str(root / "sample-target-repo")


def test_api_discover_endpoint():
    response = client.post(
        "/api/discover",
        json={
            "target_path": get_sample_target_repo(),
            "suite_rel_path": "tests/unit",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "tree" in data
    assert data["suite"] == "tests/unit"
    assert data["total_nodes"] > 0


def test_api_discover_invalid_path():
    response = client.post("/api/discover", json={
        "target_path": "/invalid/nonexistent/path/xyz999"
    })
    assert response.status_code == 400
