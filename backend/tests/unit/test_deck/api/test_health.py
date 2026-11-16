import pytest

from test_deck.api.health import health_check


@pytest.mark.anyio
async def test_health_check_returns_ok():
    data = await health_check()
    assert data["service"] == "PytestDeck"
    assert "environment" in data
