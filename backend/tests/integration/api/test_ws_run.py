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


