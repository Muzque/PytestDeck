from pathlib import Path

import pytest
from fastapi import Response

from test_deck.api.history import (
    DeleteRunsRequest,
    PruneBranchesRequest,
    PruneRunsRequest,
    SaveRunOptionsRequest,
    delete_test_runs,
    get_run_options,
    get_test_runs,
    prune_merged_and_deleted_branches,
    prune_orphaned_runs,
    save_run_options,
)
from test_deck.infrastructure.history_db import HistoryDatabase


@pytest.mark.anyio
async def test_history_endpoints_crud_and_prune(tmp_path: Path, monkeypatch):
    unit_dir = tmp_path / "tests" / "unit"
    unit_dir.mkdir(parents=True)
    (unit_dir / "test_a.py").write_text("def test_1(): pass\n", encoding="utf-8")
    (unit_dir / "test_b.py").write_text("def test_2(): pass\n", encoding="utf-8")

    db_file = tmp_path / "history.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(db_file))
    db = HistoryDatabase(target_path=tmp_path, db_path=db_file)
    db.save_run("tests/unit/test_a.py::test_1", outcome="passed", duration=0.05)
    db.save_run("tests/unit/test_b.py::test_2", outcome="failed", duration=0.12)

    resp = Response()
    all_payload = await get_test_runs(
        response=resp, target_path=str(tmp_path), node_id=None, include_branch=True
    )
    assert "runs" in all_payload
    assert "branch" in all_payload
    assert len(all_payload["runs"]) == 2

    single_payload = await get_test_runs(
        response=resp,
        target_path=str(tmp_path),
        node_id="tests/unit/test_a.py::test_1",
        include_branch=True,
    )
    assert single_payload["run"]["outcome"] == "passed"

    pruned = await prune_orphaned_runs(
        PruneRunsRequest(
            target_path=str(tmp_path),
            valid_nodes=["tests/unit/test_a.py::test_1"],
        )
    )
    assert pruned["pruned_count"] == 1

    del_one = await delete_test_runs(
        DeleteRunsRequest(
            target_path=str(tmp_path),
            node_id="tests/unit/test_a.py::test_1",
        )
    )
    assert del_one["deleted_count"] == 1

    del_all = await delete_test_runs(DeleteRunsRequest(target_path=str(tmp_path)))
    assert del_all["success"] is True

    branch_prune = await prune_merged_and_deleted_branches(
        PruneBranchesRequest(target_path=str(tmp_path))
    )
    assert branch_prune["success"] is True


@pytest.mark.anyio
async def test_run_options_endpoints_save_and_get(tmp_path: Path, monkeypatch):
    db_file = tmp_path / "history.db"
    monkeypatch.setenv("PYTESTDECK_DB_PATH", str(db_file))

    saved = await save_run_options(
        SaveRunOptionsRequest(
            target_path=str(tmp_path),
            suite="tests/integration",
            marker_filter="slow",
            extra_args="-n 2",
        )
    )
    assert saved["suite"] == "integration"
    assert saved["marker_filter"] == "slow"

    loaded = await get_run_options(
        target_path=str(tmp_path), suite="integration", include_suites=True
    )
    assert loaded["marker_filter"] == "slow"
    assert loaded["extra_args"] == "-n 2"
    assert "suites" in loaded
    assert loaded["suites"]["integration"]["marker_filter"] == "slow"
