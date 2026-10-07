from pathlib import Path

from behave import given, then, when
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


@given("PytestDeck backend is running")
def step_backend_running(context):
    context.client = client


@when("a health request is sent")
def step_health_request(context):
    context.response = context.client.get("/api/health")


@then("the response status should be 200")
def step_response_status(context):
    assert context.response.status_code == 200


@when("a config request is sent")
def step_config_request(context):
    context.response = context.client.get("/api/config")


@then("the config response status should be 200")
def step_config_status(context):
    assert context.response.status_code == 200


@then('the config response should contain "{key}"')
def step_config_contains(context, key):
    data = context.response.json()
    assert key in data


@when('a discover request is sent for suite "{suite_path}"')
def step_discover_request(context, suite_path):
    repo_path = str(Path(__file__).resolve().parents[5] / "sample-target-repo")
    context.response = context.client.post(
        "/api/discover",
        json={"target_path": repo_path, "suite_rel_path": suite_path},
    )



@then("the discover response status should be 200")
def step_discover_status(context):
    assert context.response.status_code == 200


@then("the discovered tree total nodes should be greater than 0")
def step_discover_nodes(context):
    data = context.response.json()
    assert data.get("total_nodes", 0) > 0


@then("the discovered root tree should exist")
def step_discover_tree_exists(context):
    data = context.response.json()
    assert "tree" in data
    assert data["tree"] is not None
    assert bool(data["tree"].get("name") or data["tree"].get("path"))



@then('the discovered root tree name should be "{expected_name}"')
def step_discover_tree_name(context, expected_name):
    data = context.response.json()
    assert data["tree"].get("name") == expected_name


@when('a test detail request is sent for node "{node_id}"')
def step_detail_request(context, node_id):
    repo_path = str(Path(__file__).resolve().parents[5] / "sample-target-repo")
    context.response = context.client.post(
        "/api/test-detail",
        json={"target_path": repo_path, "node_id": node_id},
    )


@then("the test detail response status should be 200")
def step_detail_status(context):
    assert context.response.status_code == 200


@then('the test detail name should be "{expected_name}"')
def step_detail_name(context, expected_name):
    data = context.response.json()
    assert data["name"] == expected_name


@then('the test detail type should be "{expected_type}"')
def step_detail_type(context, expected_type):
    data = context.response.json()
    assert data["type"] == expected_type

