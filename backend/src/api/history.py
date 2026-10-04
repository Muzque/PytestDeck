from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from infrastructure.history_db import HistoryDatabase

router = APIRouter(prefix="/api/test-runs", tags=["history"])


class DeleteRunsRequest(BaseModel):
    target_path: str = ""
    node_id: str | None = None


class PruneRunsRequest(BaseModel):
    target_path: str = ""
    valid_nodes: list[str] = []


@router.get("")
async def get_test_runs(
    target_path: str = Query("", description="Target repo path"),
    node_id: str | None = Query(None, description="Optional node_id to fetch single run"),
):
    try:
        db = HistoryDatabase(target_path=target_path)
        if node_id:
            run = db.get_run(node_id)
            return {"run": run}
        runs = db.get_all_runs()
        return {"runs": runs}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("")
async def delete_test_runs(req: DeleteRunsRequest):
    try:
        db = HistoryDatabase(target_path=req.target_path)
        if req.node_id:
            deleted = db.delete_run(req.node_id)
            return {"success": True, "deleted_count": 1 if deleted else 0}
        count = db.clear_runs()
        return {"success": True, "deleted_count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/prune")
async def prune_orphaned_runs(req: PruneRunsRequest):
    try:
        db = HistoryDatabase(target_path=req.target_path)
        pruned_count = db.prune_orphans(req.valid_nodes)
        return {"success": True, "pruned_count": pruned_count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
