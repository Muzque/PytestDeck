import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Any

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
    """Manages SQLite persistence for API Deck environments, groups, and saved requests."""

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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_api_nodes_parent ON api_nodes(parent_id, sort_order);
                """
            )
            conn.commit()

    @staticmethod
    def _parse_json_field(raw: str | None, default: Any) -> Any:
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    def _row_to_api_env(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "base_url": row["base_url"] or "",
            "auth_type": row["auth_type"] or "none",
            "auth_config": self._parse_json_field(row["auth_config"], {}),
            "default_headers": self._parse_json_field(row["default_headers"], []),
            "is_active": bool(row["is_active"]),
        }

    def _row_to_api_node(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "parent_id": row["parent_id"],
            "node_type": row["node_type"] or "request",
            "name": row["name"],
            "sort_order": int(row["sort_order"] or 0),
            "method": row["method"] or "GET",
            "path": row["path"] or "",
            "query_params": self._parse_json_field(row["query_params"], []),
            "headers": self._parse_json_field(row["headers"], []),
            "body_type": row["body_type"] or "json",
            "body": row["body"] or "",
            "expected_status": int(row["expected_status"] or 200),
            "last_status": row["last_status"],
            "last_duration_ms": row["last_duration_ms"],
            "last_outcome": row["last_outcome"],
            "last_response_meta": self._parse_json_field(row["last_response_meta"], {}),
        }

    def list_api_environments(self) -> list[dict[str, Any]]:
        """Returns all saved API server environments ordered by creation/update."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT id, name, base_url, auth_type, auth_config, default_headers, is_active FROM api_environments ORDER BY rowid ASC"
            )
            return [self._row_to_api_env(r) for r in cur.fetchall()]

    def save_api_environment(self, env_data: dict[str, Any]) -> dict[str, Any]:
        """Creates or updates an API environment configuration."""
        env_id = str(env_data.get("id") or f"env-{uuid.uuid4().hex[:8]}")
        name = (
            str(env_data.get("name") or "Default Environment").strip()
            or "Default Environment"
        )
        base_url = str(env_data.get("base_url") or "").strip()
        auth_type = str(env_data.get("auth_type") or "none").strip().lower()
        auth_config_json = json.dumps(env_data.get("auth_config") or {})
        default_headers_json = json.dumps(env_data.get("default_headers") or [])
        is_active = 1 if env_data.get("is_active") else 0

        with self._get_connection() as conn:
            if is_active:
                conn.execute("UPDATE api_environments SET is_active = 0")
            conn.execute(
                """
                INSERT INTO api_environments (id, name, base_url, auth_type, auth_config, default_headers, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    base_url=excluded.base_url,
                    auth_type=excluded.auth_type,
                    auth_config=excluded.auth_config,
                    default_headers=excluded.default_headers,
                    is_active=excluded.is_active,
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (
                    env_id,
                    name,
                    base_url,
                    auth_type,
                    auth_config_json,
                    default_headers_json,
                    is_active,
                ),
            )
            conn.commit()
            cur = conn.execute(
                "SELECT id, name, base_url, auth_type, auth_config, default_headers, is_active FROM api_environments WHERE id = ?",
                (env_id,),
            )
            row = cur.fetchone()
            return self._row_to_api_env(row)

    def set_active_api_environment(self, env_id: str) -> bool:
        """Marks the specified environment as active and deactivates others."""
        with self._get_connection() as conn:
            conn.execute("UPDATE api_environments SET is_active = 0")
            cur = conn.execute(
                "UPDATE api_environments SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (env_id,),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_api_environment(self, env_id: str) -> bool:
        """Deletes an API environment by ID."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM api_environments WHERE id = ?", (env_id,))
            conn.commit()
            return cur.rowcount > 0

    def list_api_nodes(self) -> list[dict[str, Any]]:
        """Returns all API request and group nodes ordered by sort_order and rowid."""
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT id, parent_id, node_type, name, sort_order, method, path,
                       query_params, headers, body_type, body, expected_status,
                       last_status, last_duration_ms, last_outcome, last_response_meta
                FROM api_nodes
                ORDER BY sort_order ASC, rowid ASC
                """
            )
            return [self._row_to_api_node(r) for r in cur.fetchall()]

    def upsert_api_node(self, node_data: dict[str, Any]) -> dict[str, Any]:
        """Inserts or updates an API group or request node."""
        node_id = str(node_data.get("id") or f"api-{uuid.uuid4().hex[:8]}")
        node_type = str(node_data.get("node_type") or "request").strip().lower()
        if node_type not in ("group", "request"):
            node_type = "request"
        name = str(
            node_data.get("name")
            or ("New Group" if node_type == "group" else "New Request")
        ).strip()
        parent_id = node_data.get("parent_id") or None
        method = str(node_data.get("method") or "GET").strip().upper()
        path = str(node_data.get("path") or "").strip()
        query_params_json = json.dumps(node_data.get("query_params") or [])
        headers_json = json.dumps(node_data.get("headers") or [])
        body_type = str(node_data.get("body_type") or "json").strip().lower()
        body = str(node_data.get("body") if node_data.get("body") is not None else "")
        expected_status = int(node_data.get("expected_status") or 200)

        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT sort_order, parent_id FROM api_nodes WHERE id = ?", (node_id,)
            ).fetchone()
            if "sort_order" in node_data and node_data["sort_order"] is not None:
                sort_order = int(node_data["sort_order"])
            elif existing is not None:
                sort_order = int(existing["sort_order"] or 0)
            else:
                max_row = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM api_nodes WHERE COALESCE(parent_id, '') = COALESCE(?, '')",
                    (parent_id,),
                ).fetchone()
                sort_order = int(max_row["next_order"] if max_row else 0)

            if "parent_id" not in node_data and existing is not None:
                parent_id = existing["parent_id"]

            conn.execute(
                """
                INSERT INTO api_nodes (
                    id, parent_id, node_type, name, sort_order, method, path,
                    query_params, headers, body_type, body, expected_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    parent_id=excluded.parent_id,
                    node_type=excluded.node_type,
                    name=excluded.name,
                    sort_order=excluded.sort_order,
                    method=excluded.method,
                    path=excluded.path,
                    query_params=excluded.query_params,
                    headers=excluded.headers,
                    body_type=excluded.body_type,
                    body=excluded.body,
                    expected_status=excluded.expected_status,
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (
                    node_id,
                    parent_id,
                    node_type,
                    name,
                    sort_order,
                    method,
                    path,
                    query_params_json,
                    headers_json,
                    body_type,
                    body,
                    expected_status,
                ),
            )
            conn.commit()
            row = conn.execute(
                """
                SELECT id, parent_id, node_type, name, sort_order, method, path,
                       query_params, headers, body_type, body, expected_status,
                       last_status, last_duration_ms, last_outcome, last_response_meta
                FROM api_nodes WHERE id = ?
                """,
                (node_id,),
            ).fetchone()
            return self._row_to_api_node(row)

    def update_api_node_run_status(
        self,
        node_id: str,
        status_code: int | None,
        duration_ms: float | None,
        outcome: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Updates the last execution status, latency, and outcome for an API request node."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE api_nodes
                SET last_status = ?,
                    last_duration_ms = ?,
                    last_outcome = ?,
                    last_response_meta = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    status_code,
                    duration_ms,
                    outcome,
                    json.dumps(meta or {}),
                    node_id,
                ),
            )
            conn.commit()

    def move_api_node(
        self,
        node_id: str,
        target_parent_id: str | None = None,
        target_index: int = 0,
    ) -> dict[str, Any]:
        """Moves an API node to a new parent and sibling sort order."""
        with self._get_connection() as conn:
            siblings = conn.execute(
                """
                SELECT id FROM api_nodes
                WHERE COALESCE(parent_id, '') = COALESCE(?, '') AND id != ?
                ORDER BY sort_order ASC, rowid ASC
                """,
                (target_parent_id, node_id),
            ).fetchall()
            ordered_ids = [r["id"] for r in siblings]
            idx = max(0, min(int(target_index), len(ordered_ids)))
            ordered_ids.insert(idx, node_id)

            conn.execute(
                "UPDATE api_nodes SET parent_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (target_parent_id, node_id),
            )
            for i, sid in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE api_nodes SET sort_order = ? WHERE id = ?",
                    (i, sid),
                )
            conn.commit()
            return {"group_id": None, "nodes": self.list_api_nodes()}

    def delete_api_node(self, node_id: str) -> int:
        """Deletes an API node and recursively deletes any child nodes if it is a group."""
        with self._get_connection() as conn:
            to_delete = [node_id]
            visited: set[str] = set()
            while to_delete:
                curr = to_delete.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                children = conn.execute(
                    "SELECT id FROM api_nodes WHERE parent_id = ?", (curr,)
                ).fetchall()
                for c in children:
                    to_delete.append(c["id"])

            if not visited:
                return 0
            placeholders = ",".join(["?"] * len(visited))
            cur = conn.execute(
                f"DELETE FROM api_nodes WHERE id IN ({placeholders})",
                list(visited),
            )
            conn.commit()
            return cur.rowcount
