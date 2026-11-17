from pathlib import Path

from api_deck.infrastructure.api_deck_db import ApiDeckDatabase
from api_deck.infrastructure.api_node_repo import ApiNodeRepository


def test_api_node_repository_upsert_move_and_delete(tmp_path: Path):
    db = ApiDeckDatabase(target_path=tmp_path, db_path=tmp_path / "node_repo.db")
    db.save_api_environment({"id": "env-1", "name": "Local", "is_active": True})
    repo = ApiNodeRepository(db._get_connection)

    n1 = repo.upsert_api_node(
        {"id": "n1", "name": "First", "node_type": "request", "path": "/1"}
    )
    n2 = repo.upsert_api_node(
        {"id": "n2", "name": "Second", "node_type": "request", "path": "/2"}
    )
    assert n1["environment_id"] == "env-1"
    assert n2["sort_order"] == 1

    moved = repo.move_api_node(node_id="n2", target_parent_id=None, target_index=0)
    assert [n["id"] for n in moved["nodes"]] == ["n2", "n1"]

    repo.update_api_node_run_status("n2", 204, 5.5, "passed", {"size_bytes": 0})
    nodes = {n["id"]: n for n in repo.list_api_nodes()}
    assert nodes["n2"]["last_status"] == 204
    assert nodes["n2"]["last_outcome"] == "passed"

    assert repo.delete_api_node("n2") == 1
    assert [n["id"] for n in repo.list_api_nodes()] == ["n1"]
