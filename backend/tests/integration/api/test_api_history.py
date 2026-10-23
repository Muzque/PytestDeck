import pytest
from fastapi.testclient import TestClient

from app import app
from infrastructure.history_db import HistoryDatabase


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_db = tmp_path / "api_test.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(test_db))
    return TestClient(app)


def test_api_history_endpoints(client, tmp_path):
    # Setup test file in tmp_path
    target_repo = tmp_path / "repo"
    target_repo.mkdir()
    test_file = target_repo / "test_one.py"
    test_file.write_text("def test_run(): pass\n", encoding="utf-8")

    from infrastructure.test_detail_service import compute_file_hash

    f_hash = compute_file_hash(test_file)

    target_param = f"target_path={target_repo}"

    # Check initially empty
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert resp.json() == {"runs": {}}

    # Seed run via HistoryDatabase
    db = HistoryDatabase()
    db.save_run(
        "test_one.py::test_run",
        outcome="passed",
        output="Sample terminal output",
        code_hash="hash1",
        file_hash=f_hash,
    )

    # Fetch all
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert "test_one.py::test_run" in runs
    assert runs["test_one.py::test_run"]["outcome"] == "passed"

    # Fetch single
    resp = client.get(f"/api/test-runs?{target_param}&node_id=test_one.py::test_run")
    assert resp.status_code == 200
    assert resp.json()["run"]["code_hash"] == "hash1"

    # Prune
    resp = client.post(
        "/api/test-runs/prune",
        json={"target_path": str(target_repo), "valid_nodes": ["other.py::test"]},
    )
    assert resp.status_code == 200
    assert resp.json()["pruned_count"] == 1

    # Verify pruned
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.json() == {"runs": {}}


def test_api_history_file_modified_reset(client, tmp_path):
    target_repo = tmp_path / "my_project"
    target_repo.mkdir()
    test_file = target_repo / "test_math.py"
    test_file.write_text("def test_add(): pass\n", encoding="utf-8")

    from infrastructure.test_detail_service import compute_file_hash

    initial_hash = compute_file_hash(test_file)

    target_param = f"target_path={target_repo}"

    db = HistoryDatabase()
    db.save_run(
        "test_math.py::test_add",
        outcome="passed",
        duration=0.08,
        output="1 passed",
        file_hash=initial_hash,
    )

    # Verify initial run is returned
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert "test_math.py::test_add" in resp.json()["runs"]

    # Modify file content (simulating code edit by developer)
    test_file.write_text("def test_add():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    assert compute_file_hash(test_file) != initial_hash

    # Now GET /api/test-runs should detect file hash change and reset result
    resp = client.get(f"/api/test-runs?{target_param}")
    assert resp.status_code == 200
    assert resp.json()["runs"] == {}

    # Verify single node lookup also returns None
    resp_single = client.get(
        f"/api/test-runs?{target_param}&node_id=test_math.py::test_add"
    )
    assert resp_single.status_code == 200
    assert resp_single.json()["run"] is None


def test_api_run_options_endpoints(client):
    # Check default run options
    resp = client.get("/api/run-options")
    assert resp.status_code == 200
    assert resp.json() == {"marker_filter": "", "extra_args": ""}

    # Save run options
    post_resp = client.post(
        "/api/run-options",
        json={"marker_filter": "unit and not slow", "extra_args": "-s --tb=short"},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # Retrieve saved run options
    get_resp = client.get("/api/run-options")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["marker_filter"] == "unit and not slow"
    assert data["extra_args"] == "-s --tb=short"


def test_api_history_branch_switching(client, tmp_path):
    import subprocess

    from infrastructure.test_detail_service import compute_file_hash

    target_repo = tmp_path / "git_project"
    target_repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=target_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=target_repo, check=True)

    test_file = target_repo / "test_service.py"
    test_file.write_text("def test_ping(): pass\n", encoding="utf-8")
    f_hash = compute_file_hash(test_file)
    subprocess.run(["git", "add", "."], cwd=target_repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=target_repo, check=True, capture_output=True)

    db = HistoryDatabase(target_path=target_repo)
    db.save_run(
        "test_service.py::test_ping",
        outcome="passed",
        duration=0.03,
        output="ok on main",
        file_hash=f_hash,
    )

    resp_main = client.get(f"/api/test-runs?target_path={target_repo}&include_branch=1")
    assert resp_main.status_code == 200
    assert resp_main.json()["branch"] == "main"
    assert resp_main.json()["runs"]["test_service.py::test_ping"]["outcome"] == "passed"

    # Switch to feature-x where test_service.py is identical
    subprocess.run(["git", "checkout", "-b", "feature-x"], cwd=target_repo, check=True, capture_output=True)

    resp_feat = client.get(f"/api/test-runs?target_path={target_repo}&include_branch=1")
    assert resp_feat.status_code == 200
    assert resp_feat.json()["branch"] == "feature-x"
    assert resp_feat.json()["runs"] == {}

    # Prune and delete on feature-x should not affect main
    client.post(
        "/api/test-runs/prune",
        json={"target_path": str(target_repo), "valid_nodes": ["other.py::test_x"]},
    )
    client.request(
        "DELETE",
        "/api/test-runs",
        json={"target_path": str(target_repo), "node_id": "test_service.py::test_ping"},
    )

    # Switch back to main and verify main's passed run is still intact
    subprocess.run(["git", "checkout", "main"], cwd=target_repo, check=True, capture_output=True)
    resp_main_again = client.get(f"/api/test-runs?target_path={target_repo}&include_branch=1")
    assert resp_main_again.status_code == 200
    assert resp_main_again.json()["branch"] == "main"
    assert resp_main_again.json()["runs"]["test_service.py::test_ping"]["outcome"] == "passed"


def test_api_prune_branches_endpoint(client, tmp_path):
    import subprocess

    target_repo = tmp_path / "git_prune_api"
    target_repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=target_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=target_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=target_repo, check=True)

    test_file = target_repo / "test_service.py"
    test_file.write_text("def test_ping(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target_repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=target_repo, check=True, capture_output=True)

    db = HistoryDatabase(target_path=target_repo)
    db.save_run("test_service.py::test_ping", outcome="passed", output="main", branch="main")

    # Create and merge feat/a
    subprocess.run(["git", "checkout", "-b", "feat/a"], cwd=target_repo, check=True, capture_output=True)
    (target_repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target_repo, check=True)
    subprocess.run(["git", "commit", "-m", "feat a"], cwd=target_repo, check=True, capture_output=True)
    db.save_run("test_service.py::test_ping", outcome="passed", output="feat/a", branch="feat/a")

    # Create unmerged branch feat/unmerged
    subprocess.run(["git", "checkout", "-b", "feat/unmerged", "main"], cwd=target_repo, check=True, capture_output=True)
    (target_repo / "u.txt").write_text("u\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=target_repo, check=True)
    subprocess.run(["git", "commit", "-m", "feat unmerged"], cwd=target_repo, check=True, capture_output=True)
    db.save_run("test_service.py::test_ping", outcome="failed", output="feat/unmerged", branch="feat/unmerged")

    # Seed deleted branch
    db.save_run("test_service.py::test_ping", outcome="passed", output="feat/gone", branch="feat/gone")

    # Merge feat/a into main
    subprocess.run(["git", "checkout", "main"], cwd=target_repo, check=True, capture_output=True)
    subprocess.run(["git", "merge", "--no-ff", "feat/a", "-m", "merge feat/a"], cwd=target_repo, check=True, capture_output=True)

    resp = client.post(
        "/api/test-runs/prune-branches",
        json={"target_path": str(target_repo)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert set(payload["branches"]) == {"feat/a", "feat/gone"}
    assert payload["deleted_count"] == 2

    # Verify main and feat/unmerged remain in DB while feat/a and feat/gone are deleted
    assert db.get_run("test_service.py::test_ping", branch="main") is not None
    assert db.get_run("test_service.py::test_ping", branch="feat/unmerged") is not None
    assert db.get_run("test_service.py::test_ping", branch="feat/a") is None
    assert db.get_run("test_service.py::test_ping", branch="feat/gone") is None

    # Non-git repo should return 0 pruned and not error
    non_git = tmp_path / "plain_dir"
    non_git.mkdir()
    db.save_run("test_service.py::test_ping", outcome="passed", output="plain", branch="")
    resp_plain = client.post(
        "/api/test-runs/prune-branches",
        json={"target_path": str(non_git)},
    )
    assert resp_plain.status_code == 200
    assert resp_plain.json() == {"success": True, "branches": [], "deleted_count": 0}
    assert db.get_run("test_service.py::test_ping", branch="") is not None


