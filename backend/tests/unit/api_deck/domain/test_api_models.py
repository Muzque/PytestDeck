from api_deck.domain.api_models import (
    ApiCollectionNode,
    ApiEnvironment,
    ApiStressResult,
)


def test_api_environment_defaults():
    env = ApiEnvironment(id="env-1", name="Local")
    assert env.id == "env-1"
    assert env.name == "Local"
    assert env.base_url == ""
    assert env.auth_type == "none"
    assert env.auth_config == {}
    assert env.default_headers == []
    assert env.is_active is False


def test_api_collection_node_defaults():
    node = ApiCollectionNode(id="req-1", name="Health Check", path="/api/health")
    assert node.id == "req-1"
    assert node.node_type == "request"
    assert node.method == "GET"
    assert node.path == "/api/health"
    assert node.expected_status == 200
    assert node.query_params == []
    assert node.headers == []


def test_api_stress_result_fields():
    res = ApiStressResult(
        total_requests=10,
        concurrency=2,
        success_count=10,
        fail_count=0,
        avg_ms=4.5,
        min_ms=2.1,
        max_ms=9.3,
        p95_ms=8.8,
        rps=120.5,
        status_codes={"200": 10},
    )
    assert res.total_requests == 10
    assert res.warning_count == 0
    assert res.avg_ms == 4.5
    assert res.status_codes == {"200": 10}
