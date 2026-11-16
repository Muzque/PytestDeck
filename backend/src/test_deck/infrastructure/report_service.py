import time
import uuid
from pathlib import Path

from infrastructure.storage_service import get_target_storage_dir


def get_reports_dir(target_path: str | Path | None = None) -> Path:
    """Returns the dedicated reports directory under PytestDeck/.pytestdeck/<target_repo>/reports.

    Args:
        target_path: Absolute or relative target project directory path.

    Returns:
        Path: Resolved directory path for storing temporary test JSON reports.
    """
    storage_dir = get_target_storage_dir(target_path)
    reports_dir = storage_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def create_report_path(target_path: str | Path | None = None, prefix: str = "report") -> Path:
    """Generates a unique JSON report file path in the dedicated reports folder.

    Args:
        target_path: Target project directory path.
        prefix: Optional filename prefix (e.g. 'report' or 'discovery').

    Returns:
        Path: Unique report file path.
    """
    reports_dir = get_reports_dir(target_path)
    filename = f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.json"
    return reports_dir / filename


def cleanup_report_file(file_path: str | Path | None) -> bool:
    """Safely removes a report file if it exists.

    Args:
        file_path: File path to remove.

    Returns:
        bool: True if file was removed, False otherwise.
    """
    if not file_path:
        return False
    p = Path(file_path)
    try:
        if p.exists():
            p.unlink()
            return True
    except OSError:
        pass
    return False


def prune_stale_reports(target_path: str | Path | None = None, max_age_seconds: int = 3600) -> int:
    """Prunes stale or orphaned JSON reports older than max_age_seconds in the reports directory.

    Args:
        target_path: Target project directory path.
        max_age_seconds: Cutoff age in seconds for orphaned files (default: 1 hour).

    Returns:
        int: Number of pruned files.
    """
    try:
        reports_dir = get_reports_dir(target_path)
        if not reports_dir.exists():
            return 0

        now = time.time()
        pruned = 0
        for item in reports_dir.glob("*.json"):
            try:
                if item.is_file():
                    mtime = item.stat().st_mtime
                    if now - mtime > max_age_seconds:
                        item.unlink()
                        pruned += 1
            except OSError:
                pass
        return pruned
    except Exception:
        return 0
