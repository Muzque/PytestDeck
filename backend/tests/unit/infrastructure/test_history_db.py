from infrastructure.history_db import HistoryDatabase


def test_history_database_lifecycle(tmp_path):
    db_file = tmp_path / "test_history.db"
    db = HistoryDatabase(db_path=db_file)

    # Initially empty
    assert db.get_all_runs() == {}
    assert db.get_run("test_a.py::test_foo") is None

    # Save a run
    db.save_run(
        node_id="test_a.py::test_foo",
        outcome="passed",
        duration=0.12,
        output="Hello log output",
        code_hash="abcd1234ef",
        file_mtime=1234567.89,
    )

    run = db.get_run("test_a.py::test_foo")
    assert run is not None
    assert run["outcome"] == "passed"
    assert run["duration"] == 0.12
    assert run["output"] == "Hello log output"
    assert run["code_hash"] == "abcd1234ef"

    # Suffix lookup
    suffix_run = db.get_run("test_foo")
    assert suffix_run is not None
    assert suffix_run["node_id"] == "test_a.py::test_foo"

    # Batch save
    db.save_runs({
        "test_b.py::test_bar": {
            "outcome": "failed",
            "duration": 0.45,
            "timestamp": "12:00:00 UTC",
            "output": "Failure trace",
            "code_hash": "hash_bar",
            "file_mtime": 1000.0,
        }
    })

    all_runs = db.get_all_runs()
    assert len(all_runs) == 2
    assert "test_b.py::test_bar" in all_runs

    # Prune orphans
    pruned = db.prune_orphans(["test_b.py::test_bar"])
    assert pruned == 1
    assert db.get_run("test_a.py::test_foo") is None
    assert db.get_run("test_b.py::test_bar") is not None

    # Delete single run
    deleted = db.delete_run("test_b.py::test_bar")
    assert deleted is True
    assert db.get_all_runs() == {}


def test_history_database_target_repo_untouched(tmp_path, monkeypatch):
    mock_app_root = tmp_path / "pytestdeck_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_app_root))

    target_repo = tmp_path / "inventory_service"
    target_repo.mkdir()

    db = HistoryDatabase(target_path=target_repo)
    assert db.db_path == mock_app_root / ".pytestdeck" / "inventory_service" / "history.db"
    assert db.db_path.exists()

    # Verify target repo is completely clean and untouched
    assert list(target_repo.iterdir()) == []
    assert not (target_repo / ".pytestdeck").exists()


def test_history_database_run_options(tmp_path):
    db_file = tmp_path / "test_options.db"
    db = HistoryDatabase(db_path=db_file)

    # Defaults to empty
    initial = db.get_run_options()
    assert initial == {"marker_filter": "", "extra_args": ""}

    # Save run options
    db.save_run_options(marker_filter="smoke and not slow", extra_args="-s -v")
    saved = db.get_run_options()
    assert saved["marker_filter"] == "smoke and not slow"
    assert saved["extra_args"] == "-s -v"

    # Update run options
    db.save_run_options(marker_filter="integration", extra_args="")
    updated = db.get_run_options()
    assert updated["marker_filter"] == "integration"
    assert updated["extra_args"] == ""

