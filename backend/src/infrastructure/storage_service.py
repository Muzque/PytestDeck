import os
import tempfile
from pathlib import Path

from domain.services import resolve_target_path


def get_pytestdeck_root() -> Path:
    """Returns the root directory of the PytestDeck project.

    Checks PYTESTDECK_ROOT environment variable first, then climbs directory
    tree from this source file, and falls back to current working directory.
    """
    if "PYTESTDECK_ROOT" in os.environ:
        return Path(os.environ["PYTESTDECK_ROOT"]).resolve()

    # Find root from current file location (PytestDeck/backend/src/infrastructure/...)
    backend_infra = Path(__file__).resolve().parent
    for p in [backend_infra, *backend_infra.parents]:
        if (p / "backend").is_dir() and (
            (p / "frontend").is_dir() or (p / "Makefile").exists() or (p / "pyproject.toml").exists()
        ):
            return p

    cwd = Path.cwd().resolve()
    if cwd.name == "backend" and (cwd.parent / "backend").exists():
        return cwd.parent
    return cwd


def get_target_repo_name(target_path: str | Path | None = None) -> str:
    """Extracts a clean, descriptive directory name for the target repository.

    Never touches the target repository filesystem.
    """
    raw = str(target_path).strip() if target_path else os.getenv("TARGET_REPO", "").strip()
    if raw and raw not in (".", "/target"):
        name = Path(raw).name
        if name:
            return name
    try:
        resolved = resolve_target_path(str(target_path) if target_path else "")
        if resolved.name and resolved.name != "target":
            return resolved.name
    except Exception:
        pass
    return "target_repo"


def get_target_storage_dir(target_path: str | Path | None = None) -> Path:
    """Returns the dedicated storage directory inside PytestDeck/.pytestdeck/<target_repo>/.

    Ensures the target repository is completely untouched, storing all runtime databases
    and reports in PytestDeck's own directory structure.
    """
    root = get_pytestdeck_root()
    repo_name = get_target_repo_name(target_path)
    storage_root = root / ".pytestdeck"
    target_storage = storage_root / repo_name

    try:
        target_storage.mkdir(parents=True, exist_ok=True)
        gitignore = storage_root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n", encoding="utf-8")
        return target_storage
    except (OSError, PermissionError):
        fallback_dir = Path(tempfile.gettempdir()) / "pytestdeck" / repo_name
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir
