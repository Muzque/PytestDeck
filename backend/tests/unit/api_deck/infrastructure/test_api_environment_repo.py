from pathlib import Path

from api_deck.infrastructure.api_deck_db import ApiDeckDatabase
from api_deck.infrastructure.api_environment_repo import ApiEnvironmentRepository


def test_api_environment_repository_crud_and_active_fallback(tmp_path: Path):
    db = ApiDeckDatabase(target_path=tmp_path, db_path=tmp_path / "env_repo.db")
    repo = ApiEnvironmentRepository(db._get_connection)

    assert repo.list_api_environments() == []
    e1 = repo.save_api_environment({"id": "e1", "name": "Dev", "is_active": True})
    e2 = repo.save_api_environment({"id": "e2", "name": "Prod", "is_active": False})
    assert e1["is_active"] is True
    assert e2["is_active"] is False

    assert repo.set_active_api_environment("e2") is True
    envs = {e["id"]: e for e in repo.list_api_environments()}
    assert envs["e1"]["is_active"] is False
    assert envs["e2"]["is_active"] is True

    # Deleting active e2 falls back to activating e1
    assert repo.delete_api_environment("e2") is True
    remaining = repo.list_api_environments()
    assert len(remaining) == 1
    assert remaining[0]["id"] == "e1"
    assert remaining[0]["is_active"] is True
