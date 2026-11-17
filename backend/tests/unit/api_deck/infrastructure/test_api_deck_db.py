import sqlite3
from pathlib import Path

import pytest

from api_deck.infrastructure.api_deck_db import (
    _INITIALIZED_API_DB_INODES,
    ApiDeckDatabase,
)


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

    # Drag req-2 before req-1 -> reorders siblings at root without creating any group
    reordered = db.move_api_node(
        node_id="req-2",
        target_parent_id=None,
        target_index=0,
    )
    assert reordered["group_id"] is None
    assert [n["id"] for n in reordered["nodes"]] == ["req-2", "req-1"]
    assert all(n["node_type"] == "request" for n in reordered["nodes"])

    # Create a group manually and move both requests into it
    grp = db.upsert_api_node(
        {"id": "grp-users", "name": "Users Group", "node_type": "group"}
    )
    db.move_api_node(node_id="req-1", target_parent_id=grp["id"], target_index=0)
    db.move_api_node(node_id="req-2", target_parent_id=grp["id"], target_index=1)
    # Reorder within the group: move req-2 before req-1
    in_group = db.move_api_node(
        node_id="req-2", target_parent_id=grp["id"], target_index=0
    )
    assert in_group["group_id"] is None

    nodes = {n["id"]: n for n in db.list_api_nodes()}
    group_id = grp["id"]
    assert group_id in nodes
    assert nodes[group_id]["node_type"] == "group"
    assert nodes[group_id]["name"] == "Users Group"
    assert nodes["req-1"]["parent_id"] == group_id
    assert nodes["req-2"]["parent_id"] == group_id
    assert nodes["req-2"]["sort_order"] == 0
    assert nodes["req-1"]["sort_order"] == 1

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


def test_api_node_rename_preserves_fields_and_run_status(tmp_path: Path):
    db_file = tmp_path / "rename.db"
    db = ApiDeckDatabase(target_path=tmp_path, db_path=db_file)

    grp = db.upsert_api_node({"id": "grp-1", "name": "Old Group", "node_type": "group"})
    req = db.upsert_api_node(
        {
            "id": "req-1",
            "parent_id": grp["id"],
            "name": "Old Request",
            "node_type": "request",
            "method": "POST",
            "path": "/api/items",
            "query_params": [{"key": "q", "value": "1", "enabled": True}],
            "headers": [{"key": "X-Test", "value": "yes", "enabled": True}],
            "body_type": "json",
            "body": '{"ok": true}',
            "expected_status": 201,
        }
    )
    db.update_api_node_run_status("req-1", 201, 14.2, "passed", {"size_bytes": 64})

    # Rename group with full payload
    db.upsert_api_node({**grp, "name": "Renamed Group"})
    # Rename request with full payload
    db.upsert_api_node({**req, "name": "Renamed Request"})

    nodes = {n["id"]: n for n in db.list_api_nodes()}
    assert nodes["grp-1"]["name"] == "Renamed Group"
    assert nodes["req-1"]["name"] == "Renamed Request"
    assert nodes["req-1"]["parent_id"] == "grp-1"
    assert nodes["req-1"]["method"] == "POST"
    assert nodes["req-1"]["path"] == "/api/items"
    assert nodes["req-1"]["body"] == '{"ok": true}'
    assert nodes["req-1"]["expected_status"] == 201
    assert nodes["req-1"]["last_status"] == 201
    assert nodes["req-1"]["last_outcome"] == "passed"


def test_api_nodes_scoped_per_environment_and_isolated(tmp_path: Path):
    db_file = tmp_path / "scoped.db"
    db = ApiDeckDatabase(target_path=tmp_path, db_path=db_file)

    db.save_api_environment(
        {
            "id": "env-a",
            "name": "Env A",
            "base_url": "http://127.0.0.1:8001",
            "is_active": True,
        }
    )
    db.save_api_environment(
        {
            "id": "env-b",
            "name": "Env B",
            "base_url": "http://127.0.0.1:8002",
            "is_active": False,
        }
    )

    grp_a = db.upsert_api_node(
        {"id": "grp-a", "name": "Group A", "node_type": "group"}
    )
    req_a = db.upsert_api_node(
        {
            "id": "req-a",
            "parent_id": "grp-a",
            "name": "Request A",
            "node_type": "request",
            "method": "POST",
            "path": "/a",
            "body": '{"a": 1}',
        }
    )
    assert grp_a["environment_id"] == "env-a"
    assert req_a["environment_id"] == "env-a"
    db.update_api_node_run_status("req-a", 200, 10.0, "passed", {"size_bytes": 10})

    # Switch to Env B -> collection starts empty
    db.set_active_api_environment("env-b")
    assert db.list_api_nodes() == []

    req_b = db.upsert_api_node(
        {
            "id": "req-b",
            "name": "Request B",
            "node_type": "request",
            "method": "GET",
            "path": "/b",
        }
    )
    assert req_b["environment_id"] == "env-b"
    assert [n["id"] for n in db.list_api_nodes()] == ["req-b"]

    # Cannot attach a node in Env B to a parent in Env A
    with pytest.raises(ValueError):
        db.upsert_api_node(
            {
                "id": "req-b-bad",
                "parent_id": "grp-a",
                "name": "Bad Parent",
                "node_type": "request",
            }
        )

    with pytest.raises(ValueError):
        db.move_api_node(node_id="req-b", target_parent_id="grp-a", target_index=0)

    # Updating run status in Env B does not touch Env A
    db.update_api_node_run_status(
        "req-a", 500, 99.0, "failed", {"size_bytes": 0}, environment_id="env-b"
    )

    # Switch back to Env A -> original hierarchy, fields, and run status intact
    db.set_active_api_environment("env-a")
    nodes_a = {n["id"]: n for n in db.list_api_nodes()}
    assert set(nodes_a.keys()) == {"grp-a", "req-a"}
    assert nodes_a["req-a"]["parent_id"] == "grp-a"
    assert nodes_a["req-a"]["method"] == "POST"
    assert nodes_a["req-a"]["path"] == "/a"
    assert nodes_a["req-a"]["body"] == '{"a": 1}'
    assert nodes_a["req-a"]["last_status"] == 200
    assert nodes_a["req-a"]["last_outcome"] == "passed"

    # Deleting active Env A cascade-deletes Env A's nodes and activates Env B
    assert db.delete_api_environment("env-a") is True
    envs_remaining = db.list_api_environments()
    assert len(envs_remaining) == 1
    assert envs_remaining[0]["id"] == "env-b"
    assert envs_remaining[0]["is_active"] is True
    assert [n["id"] for n in db.list_api_nodes()] == ["req-b"]


def test_legacy_db_migration_assigns_unscoped_nodes_idempotently(tmp_path: Path):
    # Case 1: Legacy DB with existing active environment and unscoped nodes
    legacy_db_1 = tmp_path / "legacy_with_env.db"
    conn = sqlite3.connect(str(legacy_db_1))
    conn.execute(
        """
        CREATE TABLE api_environments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_url TEXT NOT NULL DEFAULT '',
            auth_type TEXT NOT NULL DEFAULT 'none',
            auth_config TEXT NOT NULL DEFAULT '{}',
            default_headers TEXT NOT NULL DEFAULT '[]',
            is_active INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE api_nodes (
            id TEXT PRIMARY KEY,
            parent_id TEXT DEFAULT NULL,
            node_type TEXT NOT NULL DEFAULT 'request',
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            method TEXT NOT NULL DEFAULT 'GET',
            path TEXT NOT NULL DEFAULT '',
            query_params TEXT NOT NULL DEFAULT '[]',
            headers TEXT NOT NULL DEFAULT '[]',
            body_type TEXT NOT NULL DEFAULT 'json',
            body TEXT NOT NULL DEFAULT '',
            expected_status INTEGER NOT NULL DEFAULT 200,
            last_status INTEGER DEFAULT NULL,
            last_duration_ms REAL DEFAULT NULL,
            last_outcome TEXT DEFAULT NULL,
            last_response_meta TEXT NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        "INSERT INTO api_environments (id, name, base_url, is_active) VALUES ('env-1', 'First', 'http://1', 0)"
    )
    conn.execute(
        "INSERT INTO api_environments (id, name, base_url, is_active) VALUES ('env-2', 'Active Env', 'http://2', 1)"
    )
    conn.execute(
        "INSERT INTO api_nodes (id, name, node_type, method, path) VALUES ('legacy-req', 'Legacy API', 'request', 'GET', '/legacy')"
    )
    conn.commit()
    conn.close()

    db1 = ApiDeckDatabase(target_path=tmp_path, db_path=legacy_db_1)
    nodes_env2 = db1.list_api_nodes()
    assert len(nodes_env2) == 1
    assert nodes_env2[0]["id"] == "legacy-req"
    assert nodes_env2[0]["environment_id"] == "env-2"

    # Switch active env to env-1 and simulate restart (clear inode cache)
    db1.set_active_api_environment("env-1")
    _INITIALIZED_API_DB_INODES.clear()
    db1_restarted = ApiDeckDatabase(target_path=tmp_path, db_path=legacy_db_1)
    assert db1_restarted.list_api_nodes() == []
    db1_restarted.set_active_api_environment("env-2")
    assert [n["id"] for n in db1_restarted.list_api_nodes()] == ["legacy-req"]

    # Case 2: Legacy DB with unscoped nodes and NO environments at all
    legacy_db_2 = tmp_path / "legacy_no_env.db"
    conn2 = sqlite3.connect(str(legacy_db_2))
    conn2.execute(
        """
        CREATE TABLE api_nodes (
            id TEXT PRIMARY KEY,
            parent_id TEXT DEFAULT NULL,
            node_type TEXT NOT NULL DEFAULT 'request',
            name TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            method TEXT NOT NULL DEFAULT 'GET',
            path TEXT NOT NULL DEFAULT '',
            query_params TEXT NOT NULL DEFAULT '[]',
            headers TEXT NOT NULL DEFAULT '[]',
            body_type TEXT NOT NULL DEFAULT 'json',
            body TEXT NOT NULL DEFAULT '',
            expected_status INTEGER NOT NULL DEFAULT 200,
            last_status INTEGER DEFAULT NULL,
            last_duration_ms REAL DEFAULT NULL,
            last_outcome TEXT DEFAULT NULL,
            last_response_meta TEXT NOT NULL DEFAULT '{}',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn2.execute(
        "INSERT INTO api_nodes (id, name, node_type, method, path) VALUES ('orphan-req', 'Orphan API', 'request', 'GET', '/orphan')"
    )
    conn2.commit()
    conn2.close()

    db2 = ApiDeckDatabase(target_path=tmp_path, db_path=legacy_db_2)
    envs2 = db2.list_api_environments()
    assert len(envs2) == 1
    assert envs2[0]["name"] == "Default Environment"
    assert envs2[0]["is_active"] is True
    nodes2 = db2.list_api_nodes()
    assert len(nodes2) == 1
    assert nodes2[0]["id"] == "orphan-req"
    assert nodes2[0]["environment_id"] == envs2[0]["id"]
