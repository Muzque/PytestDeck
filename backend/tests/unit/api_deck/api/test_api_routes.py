from pathlib import Path

from api_deck.api.api_routes import _collect_executable_nodes, _resolve_active_env
from api_deck.infrastructure.api_deck_db import ApiDeckDatabase


def test_collect_executable_nodes_expands_groups():
    nodes = [
        {"id": "grp-1", "parent_id": None, "node_type": "group", "name": "Users"},
        {"id": "req-1", "parent_id": "grp-1", "node_type": "request", "name": "List"},
        {"id": "req-2", "parent_id": None, "node_type": "request", "name": "Health"},
    ]
    selected = _collect_executable_nodes(nodes, ["grp-1"])
    assert [n["id"] for n in selected] == ["req-1"]


def test_resolve_active_env_picks_active(tmp_path: Path):
    db = ApiDeckDatabase(target_path=tmp_path, db_path=tmp_path / "history.db")
    db.save_api_environment(
        {"id": "e1", "name": "Env 1", "base_url": "http://localhost:8001", "is_active": True}
    )
    env = _resolve_active_env(db, None)
    assert env["id"] == "e1"
