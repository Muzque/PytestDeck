import os
import time

from infrastructure.report_service import (
    cleanup_report_file,
    create_report_path,
    get_reports_dir,
    prune_stale_reports,
)


def test_get_reports_dir_creates_directory_under_pytestdeck_root(tmp_path, monkeypatch):
    mock_root = tmp_path / "mock_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_root))

    target_repo = tmp_path / "sample_service"
    target_repo.mkdir()

    reports_dir = get_reports_dir(target_repo)
    assert reports_dir.exists()
    assert reports_dir.is_dir()
    assert reports_dir == mock_root / ".pytestdeck" / "sample_service" / "reports"

    gitignore = mock_root / ".pytestdeck" / ".gitignore"
    assert gitignore.exists()
    assert gitignore.read_text(encoding="utf-8") == "*\n"

    # Crucially: target repo is untouched
    assert not (target_repo / ".pytestdeck").exists()


def test_create_report_path(tmp_path, monkeypatch):
    mock_root = tmp_path / "mock_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_root))

    target_repo = tmp_path / "sample_service"
    target_repo.mkdir()

    report_path = create_report_path(target_repo, prefix="testrun")
    assert report_path.parent == mock_root / ".pytestdeck" / "sample_service" / "reports"
    assert report_path.name.startswith("testrun_")
    assert report_path.name.endswith(".json")


def test_cleanup_report_file(tmp_path):
    test_file = tmp_path / "sample.json"
    test_file.write_text("{}", encoding="utf-8")
    assert test_file.exists()

    # Cleanup existing file
    assert cleanup_report_file(test_file) is True
    assert not test_file.exists()

    # Cleanup non-existent file
    assert cleanup_report_file(test_file) is False

    # Cleanup None or empty
    assert cleanup_report_file(None) is False
    assert cleanup_report_file("") is False


def test_prune_stale_reports(tmp_path, monkeypatch):
    mock_root = tmp_path / "mock_app"
    monkeypatch.setenv("PYTESTDECK_ROOT", str(mock_root))

    target_repo = tmp_path / "sample_service"
    target_repo.mkdir()

    reports_dir = get_reports_dir(target_repo)

    old_file = reports_dir / "report_old.json"
    old_file.write_text("{}", encoding="utf-8")

    recent_file = reports_dir / "report_recent.json"
    recent_file.write_text("{}", encoding="utf-8")

    other_file = reports_dir / "keep.txt"
    other_file.write_text("keep", encoding="utf-8")

    # Artificially age the old file by 2 hours
    past_time = time.time() - 7200
    os.utime(old_file, (past_time, past_time))
    os.utime(other_file, (past_time, past_time))

    # Prune with 1 hour cutoff (3600s)
    pruned_count = prune_stale_reports(target_repo, max_age_seconds=3600)
    assert pruned_count == 1
    assert not old_file.exists()
    assert recent_file.exists()
    assert other_file.exists()
