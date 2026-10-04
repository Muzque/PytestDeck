import os
from pathlib import Path
from typing import Any


class TargetEnvNotReadyError(ValueError):
    """Raised when the target repository's environment is not usable yet."""


def apply_target_venv(env: dict[str, str]) -> dict[str, str]:
    """Points `uv run` at the dedicated target virtualenv, if configured.

    In Docker, PYTESTDECK_TARGET_VENV holds a Linux venv on a persistent volume, because the
    host's .venv is not usable inside the container. Scoped to target subprocesses only so
    PytestDeck's own environment is never affected. In host mode it is unset and `uv run`
    uses the target's own .venv.
    """
    target_venv = os.getenv("PYTESTDECK_TARGET_VENV")
    if target_venv:
        env["UV_PROJECT_ENVIRONMENT"] = target_venv
    return env


def get_target_env_status() -> dict[str, Any]:
    """Returns the current readiness and details of the target repository environment.

    Returns:
        dict[str, Any]: Dictionary containing status ('ready', 'running', or 'failed'),
            boolean 'ready' flag, and user-facing status message.
    """
    status_file = os.getenv("PYTESTDECK_ENV_STATUS_FILE")
    if not status_file:
        return {
            "status": "ready",
            "ready": True,
            "message": "Target environment is managed on host.",
        }

    path = Path(status_file)
    if not path.exists():
        return {
            "status": "ready",
            "ready": True,
            "message": "Environment status file not found; assuming ready.",
        }

    status = path.read_text(encoding="utf-8").strip()
    if status == "running":
        return {
            "status": "running",
            "ready": False,
            "message": (
                "Target environment is still being prepared (installing dependencies). "
                "Please retry in a moment."
            ),
        }
    if status == "failed":
        log_hint = os.getenv("PYTESTDECK_ENV_SYNC_LOG", "the container logs")
        return {
            "status": "failed",
            "ready": False,
            "message": f"Target environment sync failed. See {log_hint} for details.",
        }
    return {
        "status": "ready",
        "ready": True,
        "message": "Target environment is ready.",
    }


def ensure_target_env_ready() -> None:
    """Checks the status file written by the container entrypoint.

    Raises:
        TargetEnvNotReadyError: If the dependency sync is still running or has failed.
    """
    env_status = get_target_env_status()
    if not env_status["ready"]:
        raise TargetEnvNotReadyError(env_status["message"])


def get_target_env_logs(tail_lines: int = 200) -> str:
    """Reads recent log lines from the container target environment sync log file.

    Args:
        tail_lines: Maximum number of trailing log lines to return. Defaults to 200.

    Returns:
        str: Trailing log output from target dependency preparation, or empty string.
    """
    log_file = os.getenv("PYTESTDECK_ENV_SYNC_LOG")
    if not log_file:
        return ""
    p = Path(log_file)
    if not p.exists():
        return ""
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-tail_lines:])
    except Exception:
        return ""

