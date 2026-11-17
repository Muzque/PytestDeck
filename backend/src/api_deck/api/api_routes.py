from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_deck.infrastructure.api_deck_db import ApiDeckDatabase
from api_deck.infrastructure.api_runner_service import (
    execute_batch_requests,
    execute_single_request,
    execute_stress_test,
)

router = APIRouter(prefix="/api/api-deck", tags=["api-deck"])


class SaveEnvironmentRequest(BaseModel):
    target_path: str = ""
    environment: dict[str, Any] = Field(default_factory=dict)


class ActivateEnvironmentRequest(BaseModel):
    target_path: str = ""


class UpsertApiNodeRequest(BaseModel):
    target_path: str = ""
    node: dict[str, Any] = Field(default_factory=dict)


class MoveApiNodeRequest(BaseModel):
    target_path: str = ""
    node_id: str
    target_parent_id: str | None = None
    target_index: int = 0
    create_group_with_node_id: str | None = None
    group_name: str | None = None


class SendSingleApiRequest(BaseModel):
    target_path: str = ""
    node: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] | None = None
    timeout_s: float = 30.0


class RunBatchApiRequest(BaseModel):
    target_path: str = ""
    node_ids: list[str] = Field(default_factory=list)
    environment: dict[str, Any] | None = None
    concurrency: int = 5
    timeout_s: float = 30.0


class StressApiRequest(BaseModel):
    target_path: str = ""
    node: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] | None = None
    total_requests: int = 20
    concurrency: int = 5
    timeout_s: float = 30.0


def _resolve_active_env(
    db: ApiDeckDatabase, explicit_env: dict[str, Any] | None
) -> dict[str, Any]:
    if explicit_env is not None:
        return explicit_env
    envs = db.list_api_environments()
    for e in envs:
        if e.get("is_active"):
            return e
    return envs[0] if envs else {}


@router.get("/state")
async def get_api_deck_state(
    target_path: str = Query("", description="Target repository path"),
):
    try:
        db = ApiDeckDatabase(target_path=target_path)
        envs = db.list_api_environments()
        nodes = db.list_api_nodes()
        return {
            "environments": envs,
            "nodes": nodes,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/environments")
async def save_api_environment(req: SaveEnvironmentRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        saved = db.save_api_environment(req.environment)
        return {
            "success": True,
            "environment": saved,
            "environments": db.list_api_environments(),
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/environments/{env_id}/activate")
async def activate_api_environment(env_id: str, req: ActivateEnvironmentRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        db.set_active_api_environment(env_id)
        return {
            "success": True,
            "environments": db.list_api_environments(),
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/environments/{env_id}")
async def delete_api_environment(
    env_id: str,
    target_path: str = Query("", description="Target repository path"),
):
    try:
        db = ApiDeckDatabase(target_path=target_path)
        deleted = db.delete_api_environment(env_id)
        return {
            "success": deleted,
            "environments": db.list_api_environments(),
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/nodes")
async def upsert_api_node(req: UpsertApiNodeRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        saved = db.upsert_api_node(req.node)
        return {
            "success": True,
            "node": saved,
            "nodes": db.list_api_nodes(),
            "environments": db.list_api_environments(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/nodes/move")
async def move_api_node(req: MoveApiNodeRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        result = db.move_api_node(
            node_id=req.node_id,
            target_parent_id=req.target_parent_id,
            target_index=req.target_index,
            create_group_with_node_id=req.create_group_with_node_id,
            group_name=req.group_name,
        )
        return {
            "success": True,
            "group_id": result["group_id"],
            "nodes": result["nodes"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/nodes/{node_id}")
async def delete_api_node(
    node_id: str,
    target_path: str = Query("", description="Target repository path"),
):
    try:
        db = ApiDeckDatabase(target_path=target_path)
        deleted_count = db.delete_api_node(node_id)
        return {
            "success": deleted_count > 0,
            "deleted_count": deleted_count,
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/send")
async def send_single_api(req: SendSingleApiRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        saved_node = db.upsert_api_node(req.node)
        env = _resolve_active_env(db, req.environment)
        result = await execute_single_request(
            saved_node, env=env, timeout_s=req.timeout_s
        )
        db.update_api_node_run_status(
            node_id=saved_node["id"],
            status_code=result["status_code"],
            duration_ms=result["duration_ms"],
            outcome=result["outcome"],
            meta={"size_bytes": result["size_bytes"]},
        )
        return {
            "result": result,
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _collect_executable_nodes(
    all_nodes: list[dict[str, Any]], selected_ids: list[str]
) -> list[dict[str, Any]]:
    by_id = {n["id"]: n for n in all_nodes}
    children_map: dict[str, list[dict[str, Any]]] = {}
    for n in all_nodes:
        pid = n.get("parent_id")
        if pid:
            children_map.setdefault(pid, []).append(n)

    if not selected_ids:
        return [n for n in all_nodes if n.get("node_type") == "request"]

    collected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _visit(nid: str) -> None:
        node = by_id.get(nid)
        if not node:
            return
        if node.get("node_type") == "request":
            if nid not in seen:
                seen.add(nid)
                collected.append(node)
        else:
            for child in children_map.get(nid, []):
                _visit(child["id"])

    for sid in selected_ids:
        _visit(sid)
    return collected


@router.post("/run-batch")
async def run_batch_apis(req: RunBatchApiRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        all_nodes = db.list_api_nodes()
        target_nodes = _collect_executable_nodes(all_nodes, req.node_ids)
        env = _resolve_active_env(db, req.environment)
        batch = await execute_batch_requests(
            target_nodes,
            env=env,
            concurrency=req.concurrency,
            timeout_s=req.timeout_s,
        )
        for item in batch["results"]:
            if item.get("node_id"):
                db.update_api_node_run_status(
                    node_id=item["node_id"],
                    status_code=item["status_code"],
                    duration_ms=item["duration_ms"],
                    outcome=item["outcome"],
                    meta={"size_bytes": item["size_bytes"]},
                )
        return {
            "batch": batch,
            "nodes": db.list_api_nodes(),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/stress")
async def run_stress_api(req: StressApiRequest):
    try:
        db = ApiDeckDatabase(target_path=req.target_path)
        saved_node = db.upsert_api_node(req.node)
        env = _resolve_active_env(db, req.environment)
        stress = await execute_stress_test(
            node=saved_node,
            env=env,
            total_requests=req.total_requests,
            concurrency=req.concurrency,
            timeout_s=req.timeout_s,
        )
        return {"stress": stress}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.api_route("/mock/echo", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def mock_echo_endpoint(
    request: Request,
    status: int = Query(200, ge=100, le=599),
):
    """Built-in echo endpoint for testing API Deck requests, headers, query params, and bodies."""
    try:
        body: Any = await request.json()
    except Exception:
        raw = await request.body()
        body = raw.decode("utf-8", errors="replace") if raw else None
    return JSONResponse(
        status_code=status,
        content={
            "method": request.method,
            "query": dict(request.query_params),
            "headers": dict(request.headers),
            "echo": body,
        },
    )


@router.get("/mock/large")
async def mock_large_endpoint(
    lines: int = Query(300, ge=1, le=5000),
    keyword: str = Query("NEEDLE_MATCH_KEY"),
):
    """Built-in large response endpoint for verifying scrollable search in API Deck."""
    records = [
        {
            "line": i,
            "tag": keyword if i % 25 == 0 else "standard_log_entry",
            "detail": f"Payload record #{i:04d} with diagnostic telemetry data",
        }
        for i in range(1, lines + 1)
    ]
    return {"total_lines": len(records), "keyword": keyword, "records": records}
