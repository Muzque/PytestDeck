from pathlib import Path

from api_deck.infrastructure.api_deck_db import ApiDeckDatabase


def test_api_environments_crud_and_active_switch(tmp_path: Path):
    db_file = tmp_path / "history.db"
    db = ApiDeckDatabase(target_path=tmp_path, db_path=db_file)

    assert db.list_api_environments() == []

    env1 = db.save_api_environment(
        {
            "id": "env-local",
            "name": "Local Server",
            "base_url": "http://127.0.0.1:8000",
            "auth_type": "bearer",
            "auth_config": {"token": "secret-123"},
            "default_headers": [{"key": "X-App", "value": "PytestDeck", "enabled": True}],
            "is_active": True,
        }
    )
    assert env1["id"] == "env-local"
    assert env1["is_active"] is True
    assert env1["auth_config"]["token"] == "secret-123"

    env2 = db.save_api_environment(
        {
            "id": "env-staging",
            "name": "Staging Server",
            "base_url": "https://staging.example.com",
            "auth_type": "api_key",
            "auth_config": {"key": "X-API-Key", "value": "k-999", "in": "header"},
            "default_headers": [],
            "is_active": True,
        }
    )
    assert env2["is_active"] is True

    envs = db.list_api_environments()
    assert len(envs) == 2
    by_id = {e["id"]: e for e in envs}
    assert by_id["env-local"]["is_active"] is False
    assert by_id["env-staging"]["is_active"] is True

    db.set_active_api_environment("env-local")
    envs_after = {e["id"]: e for e in db.list_api_environments()}
    assert envs_after["env-local"]["is_active"] is True
    assert envs_after["env-staging"]["is_active"] is False

    deleted = db.delete_api_environment("env-staging")
    assert deleted is True
    assert len(db.list_api_environments()) == 1


def test_api_nodes_upsert_group_move_and_cascade_delete(tmp_path: Path):
    db_file = tmp_path / "history.db"
    db = ApiDeckDatabase(target_path=tmp_path, db_path=db_file)

    req1 = db.upsert_api_node(
        {
            "id": "req-1",
            "name": "Get Users",
            "node_type": "request",
            "method": "GET",
            "path": "/users",
            "query_params": [{"key": "page", "value": "1", "enabled": True}],
            "headers": [{"key": "Accept", "value": "application/json", "enabled": True}],
            "body_type": "json",
            "body": "",
            "expected_status": 200,
        }
    )
    req2 = db.upsert_api_node(
        {
            "id": "req-2",
            "name": "Create User",
            "node_type": "request",
            "method": "POST",
            "path": "/users",
            "body_type": "json",
            "body": '{"name": "Alice"}',
            "expected_status": 201,
        }
    )
    assert req1["id"] == "req-1"
    assert req2["method"] == "POST"

    # Drag req-2 onto req-1 to automatically create a group containing both
    grouped = db.move_api_node(
        node_id="req-2",
        target_parent_id=None,
        target_index=0,
        create_group_with_node_id="req-1",
        group_name="Users Group",
    )
    assert grouped["group_id"] is not None
    group_id = grouped["group_id"]

    nodes = {n["id"]: n for n in db.list_api_nodes()}
    assert group_id in nodes
    assert nodes[group_id]["node_type"] == "group"
    assert nodes[group_id]["name"] == "Users Group"
    assert nodes["req-1"]["parent_id"] == group_id
    assert nodes["req-2"]["parent_id"] == group_id

    # Update run status on req-1
    db.update_api_node_run_status(
        node_id="req-1",
        status_code=200,
        duration_ms=12.5,
        outcome="passed",
        meta={"size_bytes": 128},
    )
    updated_nodes = {n["id"]: n for n in db.list_api_nodes()}
    assert updated_nodes["req-1"]["last_status"] == 200
    assert updated_nodes["req-1"]["last_duration_ms"] == 12.5
    assert updated_nodes["req-1"]["last_outcome"] == "passed"

    # Cascade delete group removes children as well
    deleted_count = db.delete_api_node(group_id)
    assert deleted_count >= 3
    assert db.list_api_nodes() == []
