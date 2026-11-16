import httpx
import pytest

from infrastructure.api_runner_service import (
    build_resolved_request,
    execute_batch_requests,
    execute_single_request,
    execute_stress_test,
)


def _mock_transport() -> httpx.AsyncBaseTransport:
    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/users":
            return httpx.Response(
                200,
                json={
                    "users": [{"id": 1, "name": "Alice"}],
                    "query": dict(request.url.params),
                    "auth": request.headers.get("authorization"),
                    "api_key": request.headers.get("x-api-key"),
                },
            )
        if path == "/echo" and request.method == "POST":
            return httpx.Response(
                201,
                content=request.content,
                headers={"content-type": "application/json"},
            )
        if path == "/fail":
            return httpx.Response(500, json={"error": "server failure"})
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


def test_build_resolved_request_with_bearer_and_query_params():
    env = {
        "base_url": "http://127.0.0.1:8000/",
        "auth_type": "bearer",
        "auth_config": {"token": "my-jwt-token"},
        "default_headers": [{"key": "X-Env", "value": "local", "enabled": True}],
    }
    node = {
        "method": "GET",
        "path": "/users",
        "query_params": [
            {"key": "role", "value": "admin", "enabled": True},
            {"key": "ignored", "value": "1", "enabled": False},
        ],
        "headers": [{"key": "X-Custom", "value": "val", "enabled": True}],
        "body_type": "json",
        "body": "",
    }
    resolved = build_resolved_request(node, env)
    assert resolved["method"] == "GET"
    assert resolved["url"] == "http://127.0.0.1:8000/users"
    assert resolved["params"] == {"role": "admin"}
    assert resolved["headers"]["Authorization"] == "Bearer my-jwt-token"
    assert resolved["headers"]["X-Env"] == "local"
    assert resolved["headers"]["X-Custom"] == "val"


@pytest.mark.anyio
async def test_execute_single_and_batch_requests():
    transport = _mock_transport()
    env = {
        "base_url": "http://test.local",
        "auth_type": "bearer",
        "auth_config": {"token": "tok-1"},
        "default_headers": [],
    }
    node1 = {
        "id": "req-1",
        "name": "Get Users",
        "method": "GET",
        "path": "/users",
        "query_params": [{"key": "active", "value": "true", "enabled": True}],
        "headers": [],
        "body_type": "json",
        "body": "",
        "expected_status": 200,
    }
    node2 = {
        "id": "req-2",
        "name": "Fail Endpoint",
        "method": "GET",
        "path": "/fail",
        "query_params": [],
        "headers": [],
        "body_type": "json",
        "body": "",
        "expected_status": 200,
    }

    res1 = await execute_single_request(node1, env, transport=transport)
    assert res1["status_code"] == 200
    assert res1["outcome"] == "passed"
    assert res1["duration_ms"] >= 0.0
    assert "tok-1" in res1["body"]

    batch = await execute_batch_requests([node1, node2], env, transport=transport)
    assert batch["total"] == 2
    assert batch["passed"] == 1
    assert batch["failed"] == 1
    assert len(batch["results"]) == 2


@pytest.mark.anyio
async def test_execute_stress_test_metrics():
    transport = _mock_transport()
    env = {
        "base_url": "http://test.local",
        "auth_type": "none",
        "auth_config": {},
        "default_headers": [],
    }
    node = {
        "id": "req-stress",
        "name": "Users Stress",
        "method": "GET",
        "path": "/users",
        "query_params": [],
        "headers": [],
        "body_type": "json",
        "body": "",
        "expected_status": 200,
    }

    stress = await execute_stress_test(
        node=node,
        env=env,
        total_requests=25,
        concurrency=5,
        transport=transport,
    )
    assert stress["total_requests"] == 25
    assert stress["concurrency"] == 5
    assert stress["success_count"] == 25
    assert stress["fail_count"] == 0
    assert stress["min_ms"] >= 0.0
    assert stress["avg_ms"] >= stress["min_ms"]
    assert stress["max_ms"] >= stress["avg_ms"]
    assert stress["p95_ms"] >= stress["min_ms"]
    assert stress["status_codes"]["200"] == 25
