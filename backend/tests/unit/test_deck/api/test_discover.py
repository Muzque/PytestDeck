from test_deck.api.discover import DiscoverRequest, TestDetailRequest


def test_discover_and_detail_request_models():
    req = DiscoverRequest(target_path="/tmp/repo", suite_rel_path="tests/unit")
    assert req.target_path == "/tmp/repo"
    assert req.suite_rel_path == "tests/unit"

    detail_req = TestDetailRequest(
        target_path="/tmp/repo", node_id="tests/test_a.py::test_1"
    )
    assert detail_req.node_id == "tests/test_a.py::test_1"
