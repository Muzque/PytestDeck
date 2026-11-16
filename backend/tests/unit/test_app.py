import pytest
from fastapi import HTTPException

import app as app_module


def test_fastapi_app_title_and_routes():
    assert app_module.app.title == "PytestDeck Core API"
    assert app_module.app.version == "0.1.0"
    assert len(app_module.app.routes) >= 5


@pytest.mark.anyio
async def test_serve_spa_blocks_api_ws_and_traversal():
    if hasattr(app_module, "serve_spa"):
        with pytest.raises(HTTPException) as exc_api:
            await app_module.serve_spa("api/unknown")
        assert exc_api.value.status_code == 404

        with pytest.raises(HTTPException) as exc_ws:
            await app_module.serve_spa("ws/unknown")
        assert exc_ws.value.status_code == 404

        with pytest.raises(HTTPException) as exc_trav:
            await app_module.serve_spa("../../etc/passwd")
        assert exc_trav.value.status_code == 404
