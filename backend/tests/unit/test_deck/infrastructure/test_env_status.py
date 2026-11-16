import pytest

from infrastructure.env_status import (
    TargetEnvNotReadyError,
    apply_target_venv,
    ensure_target_env_ready,
    get_target_env_status,
)


def test_apply_target_venv_sets_project_env(monkeypatch):
    monkeypatch.setenv("PYTESTDECK_TARGET_VENV", "/cache/target_venv")
    assert apply_target_venv({})["UV_PROJECT_ENVIRONMENT"] == "/cache/target_venv"


def test_apply_target_venv_noop_when_unset(monkeypatch):
    monkeypatch.delenv("PYTESTDECK_TARGET_VENV", raising=False)
    assert "UV_PROJECT_ENVIRONMENT" not in apply_target_venv({})


def test_no_status_file_env_is_noop(monkeypatch):
    monkeypatch.delenv("PYTESTDECK_ENV_STATUS_FILE", raising=False)
    ensure_target_env_ready()


def test_missing_status_file_is_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(tmp_path / "missing"))
    ensure_target_env_ready()


def test_ready_status_passes(monkeypatch, tmp_path):
    status = tmp_path / "env_status"
    status.write_text("ready\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status))
    ensure_target_env_ready()


@pytest.mark.parametrize("value,match", [("running", "still being prepared"), ("failed", "sync failed")])
def test_not_ready_statuses_raise(monkeypatch, tmp_path, value, match):
    status = tmp_path / "env_status"
    status.write_text(value, encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status))
    with pytest.raises(TargetEnvNotReadyError, match=match):
        ensure_target_env_ready()


def test_get_target_env_status_running(monkeypatch, tmp_path):
    status = tmp_path / "env_status"
    status.write_text("running\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status))

    res = get_target_env_status()
    assert res["status"] == "running"
    assert res["ready"] is False


def test_get_target_env_status_ready(monkeypatch, tmp_path):
    status = tmp_path / "env_status"
    status.write_text("ready\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status))

    res = get_target_env_status()
    assert res["status"] == "ready"
    assert res["ready"] is True


def test_get_target_env_logs(monkeypatch, tmp_path):
    from infrastructure.env_status import get_target_env_logs

    monkeypatch.delenv("PYTESTDECK_ENV_SYNC_LOG", raising=False)
    assert get_target_env_logs() == ""

    log_file = tmp_path / "sync.log"
    monkeypatch.setenv("PYTESTDECK_ENV_SYNC_LOG", str(log_file))
    assert get_target_env_logs() == ""

    log_file.write_text("line 1\nline 2\nline 3\nline 4\n", encoding="utf-8")
    assert get_target_env_logs(tail_lines=2) == "line 3\nline 4"


