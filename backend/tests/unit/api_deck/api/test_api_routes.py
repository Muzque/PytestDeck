from pathlib import Path

import pytest

from api_deck.api.api_routes import (
    ActivateEnvironmentRequest,
    MoveApiNodeRequest,
    RunBatchApiRequest,
    SaveEnvironmentRequest,
    SendSingleApiRequest,
    StressApiRequest,
    UpsertApiNodeRequest,
    _collect_executable_nodes,
    _resolve_active_env,
    activate_api_environment,
    delete_api_environment,
    delete_api_node,
    get_api_deck_state,
    mock_large_endpoint,
    move_api_node,
    run_batch_apis,
    run_stress_api,
    save_api_environment,
    send_single_api,
    upsert_api_node,
)
from api_deck.infrastructure.api_deck_db import ApiDeckDatabase


def test_collect_executable_nodes_expands_groups_and_defaults_to_all():
    nodes = [
        {"id": "grp-1", "parent_id": None, "node_type": "group", "name": "Users"},
        {"id": "req-1", "parent_id": "grp-1", "node_type": "request", "name": "List"},
        {"id": "req-2", "parent_id": None, "node_type": "request", "name": "Health"},
    ]
    selected = _collect_executable_nodes(nodes, ["grp-1"])
    assert [n["id"] for n in selected] == ["req-1"]

    all_reqs = _collect_executable_nodes(nodes, [])
    assert [n["id"] for n in all_reqs] == ["req-1", "req-2"]


def test_resolve_active_env_picks_active_or_explicit(tmp_path: Path):
    db = ApiDeckDatabase(target_path=tmp_path, db_path=tmp_path / "api_deck.db")
    db.save_api_environment(
        {"id": "e1", "name": "Env 1", "base_url": "http://localhost:8001", "is_active": True}
    )
    env = _resolve_active_env(db, None)
    assert env["id"] == "e1"

    explicit = _resolve_active_env(db, {"id": "custom", "base_url": "http://custom"})
    assert explicit["id"] == "custom"


@pytest.mark.anyio
async def test_api_routes_environment_and_node_handlers(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "api_deck.db"
    monkeypatch.setenv("PYTESTDECK_API_DB_PATH", str(db_file))

    state = await get_api_deck_state(target_path=str(tmp_path))
    assert state == {"environments": [], "nodes": []}

    saved_env = await save_api_environment(
        SaveEnvironmentRequest(
            target_path=str(tmp_path),
            environment={"id": "env-a", "name": "Alpha", "base_url": "http://localhost", "is_active": False},
        )
    )
    assert saved_env["success"] is True
    assert saved_env["environment"]["id"] == "env-a"

    activated = await activate_api_environment(
        "env-a", ActivateEnvironmentRequest(target_path=str(tmp_path))
    )
    assert activated["environments"][0]["is_active"] is True

    n1 = await upsert_api_node(
        UpsertApiNodeRequest(
            target_path=str(tmp_path),
            node={"id": "r1", "name": "Req 1", "node_type": "request", "method": "GET", "path": "/p1"},
        )
    )
    n2 = await upsert_api_node(
        UpsertApiNodeRequest(
            target_path=str(tmp_path),
            node={"id": "r2", "name": "Req 2", "node_type": "request", "method": "POST", "path": "/p2"},
        )
    )
    assert n1["node"]["id"] == "r1"
    assert len(n2["nodes"]) == 2

    # Move r2 before r1 as siblings (does not auto-create a group)
    moved = await move_api_node(
        MoveApiNodeRequest(
            target_path=str(tmp_path),
            node_id="r2",
            target_parent_id=None,
            target_index=0,
        )
    )
    assert moved["group_id"] is None
    assert [n["id"] for n in moved["nodes"]] == ["r2", "r1"]
    assert all(n["node_type"] == "request" for n in moved["nodes"])

    # Create a group manually, move r1 & r2 into it, then cascade delete
    grp = await upsert_api_node(
        UpsertApiNodeRequest(
            target_path=str(tmp_path),
            node={"id": "grp-1", "name": "Grouped", "node_type": "group"},
        )
    )
    await move_api_node(
        MoveApiNodeRequest(
            target_path=str(tmp_path),
            node_id="r1",
            target_parent_id=grp["node"]["id"],
            target_index=0,
        )
    )
    await move_api_node(
        MoveApiNodeRequest(
            target_path=str(tmp_path),
            node_id="r2",
            target_parent_id=grp["node"]["id"],
            target_index=1,
        )
    )

    del_node = await delete_api_node(grp["node"]["id"], target_path=str(tmp_path))
    assert del_node["deleted_count"] == 3
    assert del_node["nodes"] == []

    del_env = await delete_api_environment("env-a", target_path=str(tmp_path))
    assert del_env["success"] is True


@pytest.mark.anyio
async def test_api_routes_send_batch_stress_and_mock_large(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "api_deck.db"
    monkeypatch.setenv("PYTESTDECK_API_DB_PATH", str(db_file))

    async def fake_single(node, env=None, timeout_s=30.0):
        return {
            "node_id": node.get("id"),
            "name": node.get("name"),
            "method": node.get("method", "GET"),
            "url": "http://mock/ok",
            "status_code": 200,
            "duration_ms": 3.2,
            "size_bytes": 42,
            "headers": {},
            "body": '{"ok": true}',
            "outcome": "passed",
            "error": None,
        }

    async def fake_batch(nodes, env=None, concurrency=5, timeout_s=30.0):
        return {
            "total": len(nodes),
            "passed": len(nodes),
            "failed": 0,
            "avg_ms": 2.5,
            "total_ms": 5.0,
            "results": [await fake_single(n) for n in nodes],
        }

    async def fake_stress(node, env=None, total_requests=10, concurrency=2, timeout_s=30.0):
        return {
            "node_id": node.get("id"),
            "total_requests": total_requests,
            "concurrency": concurrency,
            "success_count": total_requests,
            "fail_count": 0,
            "avg_ms": 1.5,
            "min_ms": 1.0,
            "max_ms": 2.5,
            "p95_ms": 2.2,
            "rps": 500.0,
            "status_codes": {"200": total_requests},
            "errors": [],
            "latency_samples": [1.5] * total_requests,
        }

    import api_deck.api.api_routes as routes_mod

    monkeypatch.setattr(routes_mod, "execute_single_request", fake_single)
    monkeypatch.setattr(routes_mod, "execute_batch_requests", fake_batch)
    monkeypatch.setattr(routes_mod, "execute_stress_test", fake_stress)

    send_res = await send_single_api(
        SendSingleApiRequest(
            target_path=str(tmp_path),
            node={"id": "req-x", "name": "Test X", "method": "GET", "path": "/ok"},
        )
    )
    assert send_res["result"]["status_code"] == 200
    assert send_res["nodes"][0]["last_outcome"] == "passed"

    batch_res = await run_batch_apis(
        RunBatchApiRequest(target_path=str(tmp_path), node_ids=["req-x"])
    )
    assert batch_res["batch"]["total"] == 1
    assert batch_res["batch"]["passed"] == 1

    stress_res = await run_stress_api(
        StressApiRequest(
            target_path=str(tmp_path),
            node={"id": "req-x", "name": "Test X", "method": "GET", "path": "/ok"},
            total_requests=8,
            concurrency=2,
        )
    )
    assert stress_res["stress"]["total_requests"] == 8
    assert stress_res["stress"]["avg_ms"] == 1.5

    large_payload = await mock_large_endpoint(lines=50, keyword="NEEDLE")
    assert large_payload["total_lines"] == 50
    assert any(r["tag"] == "NEEDLE" for r in large_payload["records"])


@pytest.mark.anyio
async def test_api_routes_scope_collections_by_environment(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "api_deck_env_scope.db"
    monkeypatch.setenv("PYTESTDECK_API_DB_PATH", str(db_file))

    await save_api_environment(
        SaveEnvironmentRequest(
            target_path=str(tmp_path),
            environment={
                "id": "env-a",
                "name": "Env A",
                "base_url": "http://localhost:8001",
                "is_active": True,
            },
        )
    )
    await upsert_api_node(
        UpsertApiNodeRequest(
            target_path=str(tmp_path),
            node={"id": "req-a", "name": "Req A", "node_type": "request", "method": "GET", "path": "/a"},
        )
    )

    # Save and activate Env B -> nodes for Env B are empty
    env_b_res = await save_api_environment(
        SaveEnvironmentRequest(
            target_path=str(tmp_path),
            environment={
                "id": "env-b",
                "name": "Env B",
                "base_url": "http://localhost:8002",
                "is_active": True,
            },
        )
    )
    assert env_b_res["nodes"] == []
    state_b = await get_api_deck_state(target_path=str(tmp_path))
    assert state_b["nodes"] == []

    await upsert_api_node(
        UpsertApiNodeRequest(
            target_path=str(tmp_path),
            node={"id": "req-b", "name": "Req B", "node_type": "request", "method": "GET", "path": "/b"},
        )
    )

    # Switching back to Env A returns only Env A's nodes
    act_a = await activate_api_environment(
        "env-a", ActivateEnvironmentRequest(target_path=str(tmp_path))
    )
    assert [n["id"] for n in act_a["nodes"]] == ["req-a"]

    # Deleting Env A cascade-deletes req-a, activates Env B, and returns Env B's nodes
    del_a = await delete_api_environment("env-a", target_path=str(tmp_path))
    assert del_a["success"] is True
    assert [n["id"] for n in del_a["nodes"]] == ["req-b"]
