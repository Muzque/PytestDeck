import os
import subprocess
import tempfile
from collections.abc import Iterable
from pathlib import Path

from domain.services import resolve_target_path

PROTECTED_BRANCHES: frozenset[str] = frozenset({"main", "master", "develop", ""})



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


def get_target_git_branch(target_path: str | Path | None = None) -> str:
    """Returns the current Git branch identifier for the target repository.

    - Named branch: returns branch name (e.g. 'main', 'feat/xyz')
    - Detached HEAD: returns 'detached:<short-sha>'
    - Non-git directory or unresolved path: returns ''
    """
    if target_path is None or str(target_path).strip() == "":
        return ""
    try:
        raw = str(target_path).strip()
        candidate = Path(raw)
        if candidate.is_absolute() and candidate.exists():
            target_dir = candidate.resolve()
        else:
            target_dir = resolve_target_path(raw)
    except Exception:
        return ""

    if not target_dir.exists() or not target_dir.is_dir():
        return ""

    env = dict(os.environ)
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        if target_dir.is_relative_to(tmp_root):
            env["GIT_CEILING_DIRECTORIES"] = str(target_dir.parent)
    except Exception:
        pass

    try:
        sym = subprocess.run(
            ["git", "-C", str(target_dir), "symbolic-ref", "--quiet", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
            env=env,
            check=False,
        )
        if sym.returncode == 0 and sym.stdout.strip():
            return sym.stdout.strip()

        rev = subprocess.run(
            ["git", "-C", str(target_dir), "rev-parse", "--verify", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2.0,
            env=env,
            check=False,
        )
        if rev.returncode == 0 and rev.stdout.strip():
            return f"detached:{rev.stdout.strip()}"
    except Exception:
        pass

    return ""


def get_prunable_git_branches(
    target_path: str | Path | None,
    stored_branches: Iterable[str],
) -> list[str]:
    """Determines which stored branch names in the target repository are safe to prune.

    A stored branch is prunable if:
    - The target repository is a valid Git repository (current_branch != ""), AND
    - The branch is NOT the currently active branch and NOT a protected trunk branch
      ('main', 'master', 'develop', ''), AND
    - Either the branch no longer exists in local `refs/heads/` OR it is already
      merged into HEAD or a local trunk branch (`git branch --merged`).
    """
    current_branch = get_target_git_branch(target_path)
    if not current_branch:
        return []

    try:
        raw = str(target_path).strip()
        candidate = Path(raw)
        if candidate.is_absolute() and candidate.exists():
            target_dir = candidate.resolve()
        else:
            target_dir = resolve_target_path(raw)
    except Exception:
        return []

    if not target_dir.exists() or not target_dir.is_dir():
        return []

    env = dict(os.environ)
    tmp_root = Path(tempfile.gettempdir()).resolve()
    try:
        if target_dir.is_relative_to(tmp_root):
            env["GIT_CEILING_DIRECTORIES"] = str(target_dir.parent)
    except Exception:
        pass

    local_branches: set[str] = set()
    merged_branches: set[str] = set()

    try:
        refs_res = subprocess.run(
            [
                "git",
                "-C",
                str(target_dir),
                "for-each-ref",
                "--format=%(refname:short)",
                "refs/heads/",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            env=env,
            check=False,
        )
        if refs_res.returncode != 0:
            return []
        local_branches = {
            line.strip() for line in refs_res.stdout.splitlines() if line.strip()
        }

        merge_targets = ["HEAD"] + [
            trunk for trunk in ("main", "master", "develop") if trunk in local_branches
        ]
        for ref_target in dict.fromkeys(merge_targets):
            merged_res = subprocess.run(
                [
                    "git",
                    "-C",
                    str(target_dir),
                    "branch",
                    "--merged",
                    ref_target,
                    "--format=%(refname:short)",
                ],
                capture_output=True,
                text=True,
                timeout=2.0,
                env=env,
                check=False,
            )
            if merged_res.returncode == 0:
                for line in merged_res.stdout.splitlines():
                    b_name = line.strip()
                    if b_name:
                        merged_branches.add(b_name)
    except Exception:
        return []

    prunable: list[str] = []
    seen: set[str] = set()
    for branch in stored_branches:
        if not branch or branch in seen:
            continue
        seen.add(branch)
        if branch == current_branch or branch in PROTECTED_BRANCHES:
            continue
        if branch not in local_branches or branch in merged_branches:
            prunable.append(branch)

    return sorted(prunable)


