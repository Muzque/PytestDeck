from pathlib import Path

import pytest
from fastapi import Response

from test_deck.api.health import health_check, health_logs, readiness_check


@pytest.mark.anyio
async def test_health_readiness_and_logs(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("PYTESTDECK_ENV_STATUS_FILE", raising=False)
    data = await health_check()
    assert data["service"] == "PytestDeck"
    assert data["environment"]["ready"] is True

    resp = Response()
    ready_data = await readiness_check(resp)
    assert ready_data["status"] == "ready"

    status_file = tmp_path / "status"
    status_file.write_text("running\n", encoding="utf-8")
    log_file = tmp_path / "sync.log"
    log_file.write_text("Step 1\nStep 2\n", encoding="utf-8")
    monkeypatch.setenv("PYTESTDECK_ENV_STATUS_FILE", str(status_file))
    monkeypatch.setenv("PYTESTDECK_ENV_SYNC_LOG", str(log_file))

    resp_busy = Response()
    not_ready = await readiness_check(resp_busy)
    assert resp_busy.status_code == 503
    assert not_ready["environment"]["ready"] is False

    logs_payload = await health_logs(tail=10)
    assert "Step 1" in logs_payload["logs"]
