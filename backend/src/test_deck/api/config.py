import os

from fastapi import APIRouter

from domain.services import resolve_target_path
from infrastructure.discovery_service import get_env_config

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config(target_path: str | None = None):
    raw_target = target_path or os.getenv("TARGET_REPO", "")
    resolved = resolve_target_path(raw_target)
    cfg = get_env_config(str(resolved))
    default_target_path = str(resolve_target_path(os.getenv("TARGET_REPO", "")))
    return {"config": cfg, "default_target_path": default_target_path}
