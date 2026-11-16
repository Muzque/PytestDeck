from typing import Any

from fastapi import APIRouter, Response, status

from infrastructure.env_status import get_target_env_logs, get_target_env_status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    """Returns general service liveness and current target environment preparation status."""
    env_status = get_target_env_status()
    if not env_status["ready"]:
        env_status["recent_logs"] = get_target_env_logs(tail_lines=30)
    return {
        "status": "ok",
        "service": "PytestDeck",
        "environment": env_status,
    }


@router.get("/health/ready")
async def readiness_check(response: Response):
    """Returns 200 OK when target environment is ready, or 503 when preparing or failed."""
    env_status = get_target_env_status()
    if not env_status["ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if env_status["ready"] else env_status["status"],
        "service": "PytestDeck",
        "environment": env_status,
    }


@router.get("/health/logs")
async def health_logs(tail: int = 200) -> dict[str, Any]:
    """Returns recent log lines from target environment preparation."""
    env_status = get_target_env_status()
    logs = get_target_env_logs(tail_lines=tail)
    return {
        "status": env_status["status"],
        "ready": env_status["ready"],
        "logs": logs,
    }

