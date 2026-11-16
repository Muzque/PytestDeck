from test_deck.api.history import (
    DeleteRunsRequest,
    PruneBranchesRequest,
    SaveRunOptionsRequest,
)


def test_history_request_models_defaults():
    del_req = DeleteRunsRequest()
    assert del_req.target_path == ""
    assert del_req.node_id is None

    prune_req = PruneBranchesRequest(target_path="/tmp/repo")
    assert prune_req.target_path == "/tmp/repo"

    opt_req = SaveRunOptionsRequest(suite="unit", marker_filter="smoke")
    assert opt_req.suite == "unit"
    assert opt_req.marker_filter == "smoke"
