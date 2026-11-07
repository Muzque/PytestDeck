from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_sample_target_repo() -> str:
    cwd = Path.cwd().resolve()
    root = cwd.parent if cwd.name == "backend" else cwd
    return str(root / "sample-target-repo")


def test_ws_run_endpoint():
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": get_sample_target_repo(),
            "nodes": ["tests/unit/test_calculator.py"],
        })
        msg = websocket.receive_json()
        assert msg.get("type") == "status"


def test_ws_run_invalid_target_path():
    """Verifies error message and connection closure when target_path is invalid."""
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": "/invalid/nonexistent/path/pytestdeck"
        })
        msg = websocket.receive_json()
        assert msg.get("type") == "error"
        assert "Invalid target_path" in msg.get("message", "")


def test_ws_run_stop_action():
    """Verifies STOP action behavior in websocket handler."""
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({"action": "STOP"})


def test_ws_run_unsafe_node_path():
    """Verifies error message when unsafe path traversal node is supplied."""
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": get_sample_target_repo(),
            "nodes": ["../../etc/passwd"]
        })
        msg = websocket.receive_json()
        assert msg.get("type") == "error"
        assert "Unsafe node path traversal" in msg.get("message", "")


def test_ws_run_invalid_json():
    """Verifies general error handling when malformed JSON text is sent."""
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_text("this is not json")
        msg = websocket.receive_json()
        assert msg.get("type") == "error"


def test_ws_run_behave_streaming_sequential_steps():
    """Verifies that Behave test runs stream every step sequentially without cursor-up and retain log output."""
    backend_path = str(Path(__file__).resolve().parents[3])
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": backend_path,
            "nodes": ["tests/acceptance/features/api_health.feature"],
        })
        messages = []
        while True:
            msg = websocket.receive_json()
            messages.append(msg)
            if msg.get("type") == "finished":
                break

    stdout_lines = [m["data"] for m in messages if m.get("type") == "stdout"]
    all_output = "".join(stdout_lines)

    import re
    clean_output = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", all_output)

    # 1. Must contain all steps in order
    assert "Given PytestDeck backend is running" in clean_output
    assert "When a health request is sent" in clean_output
    assert "Then the response status should be 200" in clean_output

    # 2. Must stream live logger output during run (even for passing scenario)
    assert any("LOG_INFO:httpx" in line for line in stdout_lines)

    # 3. Must NOT contain any cursor-up escape sequences \x1b[{n}A
    assert not any(f"\x1b[{i}A" in line for i in range(1, 10) for line in stdout_lines)


def test_ws_run_emits_ping_keepalive_during_silent_execution(tmp_path, monkeypatch):
    """Verifies that /ws/run forwards server-side ping keepalive messages during silent test runs."""
    from infrastructure.runner_service import SubprocessRunnerService

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_slow.py"
    test_file.write_text(
        "import time\n"
        "def test_slow_case():\n"
        "    time.sleep(0.2)\n"
        "    assert True\n",
        encoding="utf-8",
    )

    orig_init = SubprocessRunnerService.__init__

    def fast_heartbeat_init(self, target_path: str, heartbeat_interval: float = 0.05):
        orig_init(self, target_path, heartbeat_interval=heartbeat_interval)

    monkeypatch.setattr(SubprocessRunnerService, "__init__", fast_heartbeat_init)

    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": str(tmp_path),
            "nodes": ["tests/test_slow.py"],
        })
        messages = []
        while True:
            msg = websocket.receive_json()
            messages.append(msg)
            if msg.get("type") == "finished":
                break

    assert any(m.get("type") == "ping" for m in messages)


def _is_pid_alive(pid: int) -> bool:
    import os
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def test_ws_run_stop_aborts_silent_subprocess_immediately(tmp_path):
    """Verifies that sending STOP while a test is silently sleeping aborts the subprocess within ~1s."""
    import time

    pid_file = tmp_path / "test_pid.txt"
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_hang.py"
    test_file.write_text(
        "import os, pathlib, time\n"
        "def test_silent_hang():\n"
        f"    pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "    time.sleep(30)\n",
        encoding="utf-8",
    )

    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": str(tmp_path),
            "nodes": ["tests/test_hang.py"],
        })
        # Wait for the test to enter the silent sleep
        deadline = time.monotonic() + 10.0
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists(), "Subprocess did not start test_silent_hang in time"
        child_pid = int(pid_file.read_text().strip())
        assert _is_pid_alive(child_pid)

        stop_sent_at = time.monotonic()
        websocket.send_json({"action": "STOP"})

        # Subprocess must be terminated within 1.5s (not waiting for the 30s sleep)
        kill_deadline = time.monotonic() + 1.5
        while _is_pid_alive(child_pid) and time.monotonic() < kill_deadline:
            time.sleep(0.05)

        elapsed = time.monotonic() - stop_sent_at
        assert not _is_pid_alive(child_pid), f"Subprocess {child_pid} still alive after STOP ({elapsed:.2f}s)"
        assert elapsed < 1.5


def test_ws_run_disconnect_aborts_silent_subprocess_immediately(tmp_path):
    """Verifies that closing the WebSocket during a silent sleep aborts the subprocess within ~1s."""
    import time

    pid_file = tmp_path / "disconnect_pid.txt"
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_hang_disconnect.py"
    test_file.write_text(
        "import os, pathlib, time\n"
        "def test_silent_hang_disconnect():\n"
        f"    pathlib.Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "    time.sleep(30)\n",
        encoding="utf-8",
    )

    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": str(tmp_path),
            "nodes": ["tests/test_hang_disconnect.py"],
        })
        deadline = time.monotonic() + 10.0
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists(), "Subprocess did not start test_silent_hang_disconnect in time"
        child_pid = int(pid_file.read_text().strip())
        assert _is_pid_alive(child_pid)

        disconnect_at = time.monotonic()
        websocket.close()

    kill_deadline = time.monotonic() + 1.5
    while _is_pid_alive(child_pid) and time.monotonic() < kill_deadline:
        time.sleep(0.05)

    elapsed = time.monotonic() - disconnect_at
    assert not _is_pid_alive(child_pid), f"Subprocess {child_pid} still alive after disconnect ({elapsed:.2f}s)"
    assert elapsed < 1.5




