import json
from pathlib import Path

import pytest
from fastapi import WebSocketDisconnect

import test_deck.api.runner as runner_mod


class _FakeWebSocket:
    def __init__(self, incoming: list[str]):
        self._incoming = list(incoming)
        self.accepted = False
        self.closed = False
        self.sent_json: list[dict] = []
        self.sent_text: list[str] = []

    async def accept(self) -> None:
        self.accepted = True

    async def receive_text(self) -> str:
        if not self._incoming:
            raise WebSocketDisconnect()
        return self._incoming.pop(0)

    async def send_json(self, data: dict) -> None:
        self.sent_json.append(data)

    async def send_text(self, text: str) -> None:
        self.sent_text.append(text)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.anyio
async def test_websocket_run_rejects_invalid_target_path():
    ws = _FakeWebSocket(
        [json.dumps({"action": "START", "target_path": "/nonexistent/path/xyz987"})]
    )
    await runner_mod.websocket_run(ws)
    assert ws.accepted is True
    assert ws.closed is True
    assert any(m.get("type") == "error" for m in ws.sent_json)


@pytest.mark.anyio
async def test_websocket_run_streams_chunks_and_cleans_up(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PYTESTDECK_ROOT", str(tmp_path))

    class _FakeRunner:
        def __init__(self, target_dir: str):
            self.target_dir = target_dir
            self.proc = None
            self.aborted = False

        async def run_test_stream(self, **kwargs):
            yield json.dumps({"type": "stdout", "data": "running 1 test\r\n"})
            yield json.dumps({"type": "finished", "exit_code": 0})

        async def abort(self):
            self.aborted = True

    monkeypatch.setattr(runner_mod, "SubprocessRunnerService", _FakeRunner)

    ws = _FakeWebSocket(
        [
            json.dumps(
                {
                    "action": "START",
                    "target_path": str(tmp_path),
                    "nodes": ["tests/unit"],
                }
            )
        ]
    )
    await runner_mod.websocket_run(ws)
    assert len(ws.sent_text) == 2
    assert str(tmp_path.resolve()) not in runner_mod._ACTIVE_RUNNERS
