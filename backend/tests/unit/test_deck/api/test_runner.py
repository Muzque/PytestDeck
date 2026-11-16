from test_deck.api.runner import router


def test_runner_router_prefix():
    assert router.prefix == "/ws"
