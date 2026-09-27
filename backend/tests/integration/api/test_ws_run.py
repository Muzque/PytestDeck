from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_ws_run_endpoint():
    with client.websocket_connect("/ws/run") as websocket:
        websocket.send_json({
            "action": "START",
            "target_path": "/Users/xuandi/repo/PytestDeck",
            "nodes": ["backend/tests/unit/domain/test_models.py"]
        })
        msg = websocket.receive_json()
        assert msg.get("type") == "status"
