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
    db.save_runs(
        {
            "test_b.py::test_bar": {
                "outcome": "failed",
                "duration": 0.45,
                "timestamp": "12:00:00 UTC",
                "output": "Failure trace",
                "code_hash": "hash_bar",
                "file_mtime": 1000.0,
            }
        }
    )

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
    assert (
        db.db_path == mock_app_root / ".pytestdeck" / "inventory_service" / "history.db"
    )
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


def test_clean_stale_runs_on_file_modification(tmp_path):
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()
    test_file = repo_dir / "test_example.py"
    test_file.write_text("def test_one(): pass\n", encoding="utf-8")

    from infrastructure.test_detail_service import compute_file_hash

    initial_hash = compute_file_hash(test_file)

    db_file = tmp_path / "test_history.db"
    db = HistoryDatabase(db_path=db_file)

    db.save_run(
        node_id="test_example.py::test_one",
        outcome="passed",
        duration=0.05,
        output="test passed",
        file_hash=initial_hash,
    )

    # Clean runs while file is unmodified -> should NOT remove
    removed = db.clean_stale_runs(repo_dir)
    assert removed == []
    assert db.get_run("test_example.py::test_one") is not None

    # Modify file -> hash changes
    test_file.write_text("def test_one():\n    assert 1 == 1\n", encoding="utf-8")
    new_hash = compute_file_hash(test_file)
    assert new_hash != initial_hash

    # Clean runs -> should detect modification and delete run
    removed = db.clean_stale_runs(repo_dir)
    assert removed == ["test_example.py::test_one"]
    assert db.get_run("test_example.py::test_one") is None

    # Save run again with new hash
    db.save_run(
        node_id="test_example.py::test_one",
        outcome="passed",
        file_hash=new_hash,
    )
    assert db.get_run("test_example.py::test_one") is not None

    # Delete test file -> clean_stale_runs should prune it
    test_file.unlink()
    removed = db.clean_stale_runs(repo_dir)
    assert removed == ["test_example.py::test_one"]
    assert db.get_run("test_example.py::test_one") is None


def test_get_target_git_branch_states(tmp_path):
    import subprocess

    from infrastructure.storage_service import get_target_git_branch

    non_git_dir = tmp_path / "plain_dir"
    non_git_dir.mkdir()
    assert get_target_git_branch(non_git_dir) == ""

    git_repo = tmp_path / "git_repo"
    git_repo.mkdir()
    subprocess.run(["git", "init", "-b", "branch-a"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=git_repo, check=True)

    # Unborn branch still resolves branch name
    assert get_target_git_branch(git_repo) == "branch-a"

    f = git_repo / "test_sample.py"
    f.write_text("def test_ok(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=git_repo, check=True, capture_output=True)
    assert get_target_git_branch(git_repo) == "branch-a"

    subprocess.run(["git", "checkout", "-b", "branch-b"], cwd=git_repo, check=True, capture_output=True)
    assert get_target_git_branch(git_repo) == "branch-b"

    subprocess.run(["git", "checkout", "--detach", "HEAD"], cwd=git_repo, check=True, capture_output=True)
    detached_branch = get_target_git_branch(git_repo)
    assert detached_branch.startswith("detached:")
    assert len(detached_branch) > len("detached:")


def test_history_database_branch_isolation(tmp_path):
    import subprocess

    from infrastructure.test_detail_service import compute_file_hash

    git_repo = tmp_path / "branch_repo"
    git_repo.mkdir()
    subprocess.run(["git", "init", "-b", "branch-a"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=git_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=git_repo, check=True)

    test_file = git_repo / "test_calc.py"
    test_file.write_text("def test_add(): pass\n", encoding="utf-8")
    file_hash = compute_file_hash(test_file)
    subprocess.run(["git", "add", "."], cwd=git_repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=git_repo, check=True, capture_output=True)

    db_file = tmp_path / "branch_history.db"
    db = HistoryDatabase(target_path=git_repo, db_path=db_file)

    # Save passed result on branch-a
    db.save_run(
        node_id="test_calc.py::test_add",
        outcome="passed",
        duration=0.04,
        output="passed on branch-a",
        file_hash=file_hash,
    )
    assert db.get_run("test_calc.py::test_add")["outcome"] == "passed"
    assert "test_calc.py::test_add" in db.get_all_runs()

    # Switch to branch-b with identical test file content
    subprocess.run(["git", "checkout", "-b", "branch-b"], cwd=git_repo, check=True, capture_output=True)

    # branch-b should NOT see branch-a's run
    assert db.get_run("test_calc.py::test_add") is None
    assert db.get_all_runs() == {}

    # prune_orphans and delete_run on branch-b must NOT delete branch-a's record
    assert db.prune_orphans(["other_file.py::test_other"]) == 0
    assert db.delete_run("test_calc.py::test_add") is False

    # Save failed result for the same node_id on branch-b
    db.save_run(
        node_id="test_calc.py::test_add",
        outcome="failed",
        duration=0.09,
        output="failed on branch-b",
        file_hash=file_hash,
    )
    assert db.get_run("test_calc.py::test_add")["outcome"] == "failed"

    # Switch back to branch-a and verify branch-a still has its passed result
    subprocess.run(["git", "checkout", "branch-a"], cwd=git_repo, check=True, capture_output=True)
    run_a = db.get_run("test_calc.py::test_add")
    assert run_a is not None
    assert run_a["outcome"] == "passed"
    assert run_a["output"] == "passed on branch-a"

