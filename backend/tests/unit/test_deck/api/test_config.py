import pytest

from test_deck.api.config import get_config


@pytest.mark.anyio
async def test_get_config_returns_default_target_path(tmp_path):
    res = await get_config(target_path=str(tmp_path))
    assert "config" in res
    assert "default_target_path" in res
