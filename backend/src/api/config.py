from pathlib import Path

from fastapi import APIRouter

from infrastructure.discovery_service import parse_pytestdeck_config

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config():
    root_config = Path("pytestdeck.toml").resolve()
    cfg = parse_pytestdeck_config(root_config)
    return {"config": cfg}
