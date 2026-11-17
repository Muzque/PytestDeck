import httpx
import pytest

from api_deck.infrastructure.api_runner_service import (
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
        if path == "/forbidden":
            return httpx.Response(403, json={"error": "forbidden"})
        if path == "/no-content":
            return httpx.Response(204)
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
    assert batch["warning"] == 0
    assert batch["failed"] == 1
    assert len(batch["results"]) == 2


@pytest.mark.anyio
async def test_2xx_passes_and_4xx_warns_across_single_batch_and_stress():
    transport = _mock_transport()
    env = {
        "base_url": "http://test.local",
        "auth_type": "none",
        "auth_config": {},
        "default_headers": [],
    }
    created_node = {
        "id": "req-201",
        "name": "Create",
        "method": "POST",
        "path": "/echo",
        "body_type": "json",
        "body": '{"ok": true}',
        "expected_status": 200,  # default 200 should allow any 2xx
    }
    no_content_node = {
        "id": "req-204",
        "name": "No Content",
        "method": "DELETE",
        "path": "/no-content",
        "expected_status": 200,
    }
    forbidden_node = {
        "id": "req-403",
        "name": "Forbidden",
        "method": "GET",
        "path": "/forbidden",
        "expected_status": 200,
    }
    not_found_node = {
        "id": "req-404",
        "name": "Not Found",
        "method": "GET",
        "path": "/missing",
        "expected_status": 200,
    }
    fail_node = {
        "id": "req-500",
        "name": "Server Error",
        "method": "GET",
        "path": "/fail",
        "expected_status": 200,
    }

    assert (await execute_single_request(created_node, env, transport=transport))["outcome"] == "passed"
    assert (await execute_single_request(no_content_node, env, transport=transport))["outcome"] == "passed"
    assert (await execute_single_request(forbidden_node, env, transport=transport))["outcome"] == "warning"
    assert (await execute_single_request(not_found_node, env, transport=transport))["outcome"] == "warning"
    assert (await execute_single_request(fail_node, env, transport=transport))["outcome"] == "failed"

    # Explicit non-200 expected_status still enforces exact match
    strict_201 = {**created_node, "expected_status": 201}
    strict_201_on_200 = {"id": "req-strict", "method": "GET", "path": "/users", "expected_status": 201}
    strict_403 = {**forbidden_node, "expected_status": 403}
    assert (await execute_single_request(strict_201, env, transport=transport))["outcome"] == "passed"
    assert (await execute_single_request(strict_201_on_200, env, transport=transport))["outcome"] == "failed"
    assert (await execute_single_request(strict_403, env, transport=transport))["outcome"] == "passed"

    # Batch summary separates passed, warning, failed
    batch = await execute_batch_requests(
        [created_node, no_content_node, forbidden_node, fail_node],
        env,
        transport=transport,
    )
    assert batch["total"] == 4
    assert batch["passed"] == 2
    assert batch["warning"] == 1
    assert batch["failed"] == 1
    assert batch["passed"] + batch["warning"] + batch["failed"] == batch["total"]

    # Stress test counts 4xx as warning_count and does not add to errors or fail_count
    stress = await execute_stress_test(
        node=forbidden_node,
        env=env,
        total_requests=6,
        concurrency=2,
        transport=transport,
    )
    assert stress["success_count"] == 0
    assert stress["warning_count"] == 6
    assert stress["fail_count"] == 0
    assert stress["errors"] == []
    assert stress["status_codes"]["403"] == 6


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
