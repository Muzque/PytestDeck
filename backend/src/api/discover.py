from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from application.use_cases import DiscoverTestsUseCase

router = APIRouter(prefix="/api", tags=["discovery"])


class DiscoverRequest(BaseModel):
    target_path: str
    suite_rel_path: str = ""


@router.post("/discover")
async def discover_tests(req: DiscoverRequest):
    try:
        use_case = DiscoverTestsUseCase()
        tree = await use_case.execute(req.target_path, req.suite_rel_path)
        return tree.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
