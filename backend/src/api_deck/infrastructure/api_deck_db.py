import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from api_deck.infrastructure.api_environment_repo import ApiEnvironmentRepository
from api_deck.infrastructure.api_node_repo import ApiNodeRepository

_INITIALIZED_API_DB_INODES: dict[str, tuple[int, int]] = {}


def _resolve_api_storage_dir(target_path: str | Path | None = None) -> Path:
    """Returns the dedicated storage directory inside PytestDeck/.pytestdeck/<target_repo>/."""
    if "PYTESTDECK_ROOT" in os.environ:
        root = Path(os.environ["PYTESTDECK_ROOT"]).resolve()
    else:
        curr = Path(__file__).resolve().parent
        root = Path.cwd().resolve()
        for p in [curr, *curr.parents]:
            if (p / "backend").is_dir() and (
                (p / "frontend").is_dir() or (p / "Makefile").exists()
            ):
                root = p
                break

    raw = (
        str(target_path).strip()
        if target_path
        else os.getenv("TARGET_REPO", "").strip()
    )
    repo_name = Path(raw).name if raw and raw not in (".", "/target") else "target_repo"
    if not repo_name:
        repo_name = "target_repo"

    canonical_id = ""
    if raw and raw not in (".", "/target"):
        try:
            canonical_id = str(Path(raw).expanduser().resolve())
        except Exception:
            canonical_id = raw

    storage_root = root / ".pytestdeck"
    target_storage = storage_root / repo_name
    try:
        if canonical_id and target_storage.exists():
            marker_file = target_storage / ".target_path"
            if marker_file.exists():
                recorded_id = marker_file.read_text(encoding="utf-8").strip()
                if recorded_id and recorded_id != canonical_id:
                    short_hash = hashlib.sha256(canonical_id.encode("utf-8")).hexdigest()[:8]
                    target_storage = storage_root / f"{repo_name}-{short_hash}"
        target_storage.mkdir(parents=True, exist_ok=True)
        return target_storage
    except (OSError, PermissionError):
        fallback_dir = Path(tempfile.gettempdir()) / "pytestdeck" / repo_name
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


class ApiDeckDatabase:
    """Manages SQLite connection, schema initialization, and repositories for API Deck."""

    def __init__(
        self, target_path: str | Path | None = None, db_path: str | Path | None = None
    ):
        self.target_path = target_path
        if db_path:
            self.db_path = Path(db_path)
        else:
            custom_env = os.environ.get("PYTESTDECK_API_DB_PATH") or os.environ.get(
                "PYTESTDECK_DB_PATH"
            )
            if custom_env:
                self.db_path = Path(custom_env)
            else:
                storage_dir = _resolve_api_storage_dir(target_path)
                self.db_path = storage_dir / "api_deck.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_key = str(self.db_path.resolve())
        current_inode = self._get_file_identity()
        if (
            current_inode is None
            or _INITIALIZED_API_DB_INODES.get(resolved_key) != current_inode
        ):
            self._init_db()
            new_inode = self._get_file_identity()
            if new_inode is not None:
                _INITIALIZED_API_DB_INODES[resolved_key] = new_inode

        self._env_repo = ApiEnvironmentRepository(self._get_connection)
        self._node_repo = ApiNodeRepository(self._get_connection)

    def _get_file_identity(self) -> tuple[int, int] | None:
        try:
            st = self.db_path.stat()
            return (st.st_ino, st.st_ctime_ns)
        except OSError:
            return None

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_environments (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL DEFAULT '',
                    auth_type TEXT NOT NULL DEFAULT 'none',
                    auth_config TEXT NOT NULL DEFAULT '{}',
                    default_headers TEXT NOT NULL DEFAULT '[]',
                    is_active INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_nodes (
                    id TEXT PRIMARY KEY,
                    environment_id TEXT NOT NULL DEFAULT '',
                    parent_id TEXT DEFAULT NULL,
                    node_type TEXT NOT NULL DEFAULT 'request',
                    name TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    method TEXT NOT NULL DEFAULT 'GET',
                    path TEXT NOT NULL DEFAULT '',
                    query_params TEXT NOT NULL DEFAULT '[]',
                    headers TEXT NOT NULL DEFAULT '[]',
                    body_type TEXT NOT NULL DEFAULT 'json',
                    body TEXT NOT NULL DEFAULT '',
                    expected_status INTEGER NOT NULL DEFAULT 200,
                    last_status INTEGER DEFAULT NULL,
                    last_duration_ms REAL DEFAULT NULL,
                    last_outcome TEXT DEFAULT NULL,
                    last_response_meta TEXT NOT NULL DEFAULT '{}',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cols = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(api_nodes)").fetchall()
            }
            if "environment_id" not in cols:
                conn.execute(
                    "ALTER TABLE api_nodes ADD COLUMN environment_id TEXT NOT NULL DEFAULT ''"
                )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_api_nodes_parent ON api_nodes(parent_id, sort_order);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_api_nodes_env_parent ON api_nodes(environment_id, parent_id, sort_order);
                """
            )
            legacy_row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM api_nodes WHERE COALESCE(environment_id, '') = ''"
            ).fetchone()
            if legacy_row and int(legacy_row["cnt"]) > 0:
                target_env_id = ApiEnvironmentRepository.ensure_active_environment_id(
                    conn
                )
                conn.execute(
                    "UPDATE api_nodes SET environment_id = ? WHERE COALESCE(environment_id, '') = ''",
                    (target_env_id,),
                )
            conn.commit()

    def list_api_environments(self) -> list[dict[str, Any]]:
        """Returns all saved API server environments ordered by creation/update."""
        return self._env_repo.list_api_environments()

    def save_api_environment(self, env_data: dict[str, Any]) -> dict[str, Any]:
        """Creates or updates an API environment configuration."""
        return self._env_repo.save_api_environment(env_data)

    def set_active_api_environment(self, env_id: str) -> bool:
        """Marks the specified environment as active and deactivates others."""
        return self._env_repo.set_active_api_environment(env_id)

    def delete_api_environment(self, env_id: str) -> bool:
        """Deletes an API environment by ID, cascade-deleting its nodes and activating the next environment if needed."""
        return self._env_repo.delete_api_environment(env_id)

    def list_api_nodes(self, environment_id: str | None = None) -> list[dict[str, Any]]:
        """Returns API request and group nodes for the active (or specified) environment ordered by sort_order and rowid."""
        return self._node_repo.list_api_nodes(environment_id=environment_id)

    def upsert_api_node(
        self, node_data: dict[str, Any], environment_id: str | None = None
    ) -> dict[str, Any]:
        """Inserts or updates an API group or request node within its environment."""
        return self._node_repo.upsert_api_node(
            node_data, environment_id=environment_id
        )

    def update_api_node_run_status(
        self,
        node_id: str,
        status_code: int | None,
        duration_ms: float | None,
        outcome: str,
        meta: dict[str, Any] | None = None,
        environment_id: str | None = None,
    ) -> None:
        """Updates the last execution status, latency, and outcome for an API request node in the active environment."""
        self._node_repo.update_api_node_run_status(
            node_id=node_id,
            status_code=status_code,
            duration_ms=duration_ms,
            outcome=outcome,
            meta=meta,
            environment_id=environment_id,
        )

    def move_api_node(
        self,
        node_id: str,
        target_parent_id: str | None = None,
        target_index: int = 0,
        environment_id: str | None = None,
    ) -> dict[str, Any]:
        """Moves an API node to a new parent and sibling sort order within the same environment."""
        return self._node_repo.move_api_node(
            node_id=node_id,
            target_parent_id=target_parent_id,
            target_index=target_index,
            environment_id=environment_id,
        )

    def delete_api_node(
        self, node_id: str, environment_id: str | None = None
    ) -> int:
        """Deletes an API node in the active environment and recursively deletes any child nodes if it is a group."""
        return self._node_repo.delete_api_node(
            node_id=node_id, environment_id=environment_id
        )
