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

    # 4. Group api-2 onto api-1 via drag-and-drop move endpoint
    move_res = client.post(
        "/api/api-deck/nodes/move",
        json={
            "target_path": str(tmp_path),
            "node_id": "api-2",
            "target_parent_id": None,
            "target_index": 0,
            "create_group_with_node_id": "api-1",
            "group_name": "Core APIs",
        },
    )
    assert move_res.status_code == 200
    group_id = move_res.json()["group_id"]
    assert group_id is not None

    # 5. Verify mock endpoints directly
    mock_echo = client.post("/api/api-deck/mock/echo?q=hello", json={"msg": "world"})
    assert mock_echo.status_code == 200
    assert mock_echo.json()["echo"]["msg"] == "world"

    mock_large = client.get("/api/api-deck/mock/large?lines=120&keyword=SEARCH_TARGET")
    assert mock_large.status_code == 200
    assert "SEARCH_TARGET" in mock_large.text

    # 6. Create a second active environment -> collection is isolated per environment
    env2_res = client.post(
        "/api/api-deck/environments",
        json={
            "target_path": str(tmp_path),
            "environment": {
                "id": "env-2",
                "name": "Staging Mock",
                "base_url": "http://127.0.0.1:9388",
                "is_active": True,
            },
        },
    )
    assert env2_res.status_code == 200
    assert env2_res.json()["nodes"] == []

    state_env2 = client.get("/api/api-deck/state", params={"target_path": str(tmp_path)})
    assert state_env2.json()["nodes"] == []

    # Switching back to env-1 restores env-1's collection
    act_env1 = client.put(
        "/api/api-deck/environments/env-1/activate",
        json={"target_path": str(tmp_path)},
    )
    assert act_env1.status_code == 200
    assert len(act_env1.json()["nodes"]) == 3
