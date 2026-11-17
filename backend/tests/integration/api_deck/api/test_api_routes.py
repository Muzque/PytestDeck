from pathlib import Path

from fastapi.testclient import TestClient

from app import app


def test_api_deck_routes_end_to_end(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "history.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(db_file))
    client = TestClient(app)

    # 1. Initial state is empty
    state_res = client.get("/api/api-deck/state", params={"target_path": str(tmp_path)})
    assert state_res.status_code == 200
    state_data = state_res.json()
    assert state_data["environments"] == []
    assert state_data["nodes"] == []

    # 2. Create environment
    env_res = client.post(
        "/api/api-deck/environments",
        json={
            "target_path": str(tmp_path),
            "environment": {
                "id": "env-1",
                "name": "Local Mock",
                "base_url": "http://127.0.0.1:9388",
                "auth_type": "bearer",
                "auth_config": {"token": "demo-token"},
                "default_headers": [{"key": "X-Client", "value": "PytestDeck", "enabled": True}],
                "is_active": True,
            },
        },
    )
    assert env_res.status_code == 200
    assert env_res.json()["environment"]["is_active"] is True

    # 3. Create two API request nodes
    n1_res = client.post(
        "/api/api-deck/nodes",
        json={
            "target_path": str(tmp_path),
            "node": {
                "id": "api-1",
                "name": "Echo Test",
                "node_type": "request",
                "method": "POST",
                "path": "/api/api-deck/mock/echo",
                "query_params": [{"key": "q", "value": "hello", "enabled": True}],
                "headers": [{"key": "X-Custom", "value": "123", "enabled": True}],
                "body_type": "json",
                "body": '{"msg": "world"}',
                "expected_status": 200,
            },
        },
    )
    assert n1_res.status_code == 200

    n2_res = client.post(
        "/api/api-deck/nodes",
        json={
            "target_path": str(tmp_path),
            "node": {
                "id": "api-2",
                "name": "Large Response Test",
                "node_type": "request",
                "method": "GET",
                "path": "/api/api-deck/mock/large",
                "query_params": [{"key": "lines", "value": "150", "enabled": True}],
                "headers": [],
                "body_type": "json",
                "body": "",
                "expected_status": 200,
            },
        },
    )
    assert n2_res.status_code == 200

    # 4. Reorder api-2 before api-1 via move endpoint without auto-creating a group
    move_res = client.post(
        "/api/api-deck/nodes/move",
        json={
            "target_path": str(tmp_path),
            "node_id": "api-2",
            "target_parent_id": None,
            "target_index": 0,
        },
    )
    assert move_res.status_code == 200
    assert move_res.json()["group_id"] is None
    moved_nodes = move_res.json()["nodes"]
    assert [n["id"] for n in moved_nodes] == ["api-2", "api-1"]
    assert all(n["node_type"] == "request" for n in moved_nodes)

    # 5. Verify mock endpoints directly
    mock_echo = client.post("/api/api-deck/mock/echo?q=hello", json={"msg": "world"})
    assert mock_echo.status_code == 200
    assert mock_echo.json()["echo"]["msg"] == "world"

    mock_large = client.get("/api/api-deck/mock/large?lines=120&keyword=SEARCH_TARGET")
    assert mock_large.status_code == 200
    assert "SEARCH_TARGET" in mock_large.text
