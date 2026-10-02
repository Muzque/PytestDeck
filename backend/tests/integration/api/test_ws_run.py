from pathlib import Path

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def get_repo_root() -> str:
    cwd = Path.cwd().resolve()
    return str(cwd.parent if cwd.name == "backend" else cwd)


def test_ws_run_endpoint():
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": get_repo_root(),
            "nodes": ["backend/tests/unit/domain/test_models.py"]
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
            "target_path": get_repo_root(),
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

