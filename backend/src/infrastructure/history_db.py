import datetime
import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from infrastructure.storage_service import (
    get_prunable_git_branches,
    get_target_git_branch,
    get_target_storage_dir,
)

SUITE_SLOTS: tuple[str, ...] = ("unit", "integration", "acceptance")
_INITIALIZED_DB_INODES: dict[str, tuple[int, int]] = {}



def normalize_suite_slot(suite: str | None) -> str:
    """Normalizes a suite identifier or path into one of 'unit', 'integration', or 'acceptance'."""
    if not suite:
        return "unit"
    s = suite.strip().lower()
    if s in ("acceptance", "ac", "behave") or "acceptance" in s or s.endswith(".feature"):
        return "acceptance"
    if s in ("integration", "it") or "integration" in s:
        return "integration"
    return "unit"



class HistoryDatabase:
    """Manages SQLite persistence for individual test method run outputs, durations, outcomes, and code hashes."""

    def __init__(
        self, target_path: str | Path | None = None, db_path: str | Path | None = None
    ):
        self.target_path = target_path
        if db_path:
            self.db_path = Path(db_path)
        else:
            custom_env = os.environ.get("PYTESTDECK_DB_PATH")
            if custom_env:
                self.db_path = Path(custom_env)
            else:
                storage_dir = get_target_storage_dir(target_path)
                self.db_path = storage_dir / "history.db"

        self._ensure_storage_dir()
        resolved_key = str(self.db_path.resolve())
        current_inode = self._get_file_identity()
        if current_inode is None or _INITIALIZED_DB_INODES.get(resolved_key) != current_inode:
            self._init_db()
            new_inode = self._get_file_identity()
            if new_inode is not None:
                _INITIALIZED_DB_INODES[resolved_key] = new_inode

    def _get_file_identity(self) -> tuple[int, int] | None:
        """Returns (st_ino, st_ctime_ns) if the database file exists on disk, or None."""
        try:
            st = self.db_path.stat()
            return (st.st_ino, st.st_ctime_ns)
        except OSError:
            return None

    def get_current_branch(self, target_path: str | Path | None = None) -> str:
        """Resolves the active git branch identifier for the given or configured target path."""
        effective_target = target_path if target_path is not None else self.target_path
        return get_target_git_branch(effective_target)

    def _ensure_storage_dir(self) -> None:
        """Ensures parent directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        """Creates the test_runs table and indexes if they do not exist, migrating legacy schemas."""
        with self._get_connection() as conn:
            cur = conn.execute("PRAGMA table_info(test_runs);")
            cols = cur.fetchall()

            if not cols:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS test_runs (
                        node_id TEXT NOT NULL,
                        branch TEXT NOT NULL DEFAULT '',
                        outcome TEXT,
                        duration REAL,
                        timestamp TEXT,
                        output TEXT,
                        code_hash TEXT,
                        file_mtime REAL,
                        file_hash TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (node_id, branch)
                    );
                    """
                )
            else:
                col_names = {c["name"] for c in cols}
                if "file_hash" not in col_names:
                    try:
                        conn.execute("ALTER TABLE test_runs ADD COLUMN file_hash TEXT;")
                    except sqlite3.OperationalError:
                        pass

                has_branch_pk = any(c["name"] == "branch" and c["pk"] > 0 for c in cols)
                if not has_branch_pk:
                    default_branch = self.get_current_branch()
                    conn.execute(
                        """
                        CREATE TABLE test_runs_new (
                            node_id TEXT NOT NULL,
                            branch TEXT NOT NULL DEFAULT '',
                            outcome TEXT,
                            duration REAL,
                            timestamp TEXT,
                            output TEXT,
                            code_hash TEXT,
                            file_mtime REAL,
                            file_hash TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (node_id, branch)
                        );
                        """
                    )
                    if "branch" in col_names:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO test_runs_new
                                (node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                            SELECT node_id, COALESCE(branch, ?), outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at
                            FROM test_runs;
                            """,
                            (default_branch,),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO test_runs_new
                                (node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                            SELECT node_id, ?, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at
                            FROM test_runs;
                            """,
                            (default_branch,),
                        )
                    conn.execute("DROP TABLE test_runs;")
                    conn.execute("ALTER TABLE test_runs_new RENAME TO test_runs;")

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_runs_updated ON test_runs(updated_at);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_runs_branch ON test_runs(branch);
                """
            )
            ro_cur = conn.execute("PRAGMA table_info(run_options);")
            ro_cols = ro_cur.fetchall()
            if not ro_cols:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS run_options (
                        suite TEXT PRIMARY KEY,
                        marker_filter TEXT NOT NULL DEFAULT '',
                        extra_args TEXT NOT NULL DEFAULT '',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            else:
                ro_col_names = {c["name"] for c in ro_cols}
                if "suite" not in ro_col_names:
                    conn.execute(
                        """
                        CREATE TABLE run_options_new (
                            suite TEXT PRIMARY KEY,
                            marker_filter TEXT NOT NULL DEFAULT '',
                            extra_args TEXT NOT NULL DEFAULT '',
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        """
                    )
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO run_options_new (suite, marker_filter, extra_args, updated_at)
                        SELECT 'unit', COALESCE(marker_filter, ''), COALESCE(extra_args, ''), updated_at
                        FROM run_options
                        WHERE id = 1;
                        """
                    )
                    conn.execute("DROP TABLE run_options;")
                    conn.execute("ALTER TABLE run_options_new RENAME TO run_options;")
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


    def save_run(
        self,
        node_id: str,
        outcome: str = "unknown",
        duration: float | None = None,
        timestamp: str | None = None,
        output: str = "",
        code_hash: str | None = None,
        file_mtime: float | None = None,
        file_hash: str | None = None,
        branch: str | None = None,
    ) -> None:
        """Saves or updates a test method's execution record for the given or active git branch."""
        now_ts = timestamp or datetime.datetime.now(datetime.UTC).strftime(
            "%H:%M:%S UTC"
        )
        resolved_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_runs (node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(node_id, branch) DO UPDATE SET
                    outcome=excluded.outcome,
                    duration=excluded.duration,
                    timestamp=excluded.timestamp,
                    output=excluded.output,
                    code_hash=excluded.code_hash,
                    file_mtime=excluded.file_mtime,
                    file_hash=excluded.file_hash,
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (
                    node_id,
                    resolved_branch,
                    outcome,
                    duration,
                    now_ts,
                    output,
                    code_hash,
                    file_mtime,
                    file_hash,
                ),
            )
            conn.commit()

    def save_runs(
        self, runs: dict[str, dict[str, Any]], branch: str | None = None
    ) -> None:
        """Batch saves multiple test method execution outputs for the given or active git branch."""
        if not runs:
            return
        default_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            for node_id, data in runs.items():
                row_branch = (
                    data.get("branch")
                    if data.get("branch") is not None
                    else default_branch
                )
                conn.execute(
                    """
                    INSERT INTO test_runs (node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(node_id, branch) DO UPDATE SET
                        outcome=excluded.outcome,
                        duration=excluded.duration,
                        timestamp=excluded.timestamp,
                        output=excluded.output,
                        code_hash=excluded.code_hash,
                        file_mtime=excluded.file_mtime,
                        file_hash=excluded.file_hash,
                        updated_at=CURRENT_TIMESTAMP;
                    """,
                    (
                        node_id,
                        row_branch,
                        data.get("outcome", "unknown"),
                        data.get("duration"),
                        data.get("timestamp"),
                        data.get("output", ""),
                        data.get("code_hash"),
                        data.get("file_mtime"),
                        data.get("file_hash"),
                    ),
                )
            conn.commit()

    def get_run(
        self, node_id: str, branch: str | None = None
    ) -> dict[str, Any] | None:
        """Fetches the latest run details for a given test node ID on the active git branch."""
        resolved_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs WHERE branch = ? AND node_id = ?",
                (resolved_branch, node_id),
            )
            row = cur.fetchone()
            if row:
                return dict(row)

            # Suffix match fallback (in case relative path prefix differs)
            cur = conn.execute(
                "SELECT node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs WHERE branch = ? AND node_id LIKE ? LIMIT 1",
                (resolved_branch, f"%{node_id}"),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_runs(self, branch: str | None = None) -> dict[str, dict[str, Any]]:
        """Returns all recorded test runs for the active git branch indexed by node_id."""
        resolved_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT node_id, branch, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs WHERE branch = ? ORDER BY updated_at DESC",
                (resolved_branch,),
            )
            return {row["node_id"]: dict(row) for row in cur.fetchall()}

    def clean_stale_runs(
        self, target_path: str | Path | None = None, branch: str | None = None
    ) -> list[str]:
        """Checks stored runs for the active branch against target repo files and purges stale/modified records.

        If a test file is missing or its content/hash has been modified since the run was recorded,
        the run for the current branch is deleted from the database.
        Returns a list of node_ids that were removed.
        """
        effective_target = target_path if target_path is not None else self.target_path
        if not effective_target:
            return []
        try:
            from domain.services import resolve_target_path
            from infrastructure.test_detail_service import (
                compute_file_hash,
                get_node_code_metadata,
                resolve_test_file,
            )

            target_dir = resolve_target_path(str(effective_target))
        except Exception:
            return []

        resolved_branch = (
            self.get_current_branch(target_dir) if branch is None else branch
        )
        all_runs = self.get_all_runs(branch=resolved_branch)
        if not all_runs:
            return []

        stale_nodes: list[str] = []
        file_hash_cache: dict[str, str | None] = {}
        metadata_cache: dict[str, Any] = {}

        for node_id, data in all_runs.items():
            rel_file = node_id.split("::")[0]
            if rel_file not in file_hash_cache:
                full_path = resolve_test_file(target_dir, rel_file)
                if not full_path or not full_path.exists() or not full_path.is_file():
                    file_hash_cache[rel_file] = None
                else:
                    file_hash_cache[rel_file] = compute_file_hash(full_path)

            curr_file_hash = file_hash_cache[rel_file]
            if curr_file_hash is None:
                # Test file no longer exists
                stale_nodes.append(node_id)
                continue

            stored_file_hash = data.get("file_hash")
            stored_code_hash = data.get("code_hash")

            if stored_file_hash:
                if curr_file_hash != stored_file_hash:
                    stale_nodes.append(node_id)
            elif stored_code_hash:
                curr_code_hash, _ = get_node_code_metadata(
                    target_dir, node_id, cache=metadata_cache
                )
                if curr_code_hash != stored_code_hash:
                    stale_nodes.append(node_id)
            else:
                stored_mtime = data.get("file_mtime")
                if stored_mtime:
                    _, curr_mtime = get_node_code_metadata(
                        target_dir, node_id, cache=metadata_cache
                    )
                    if curr_mtime and curr_mtime > stored_mtime + 1.0:
                        stale_nodes.append(node_id)

        for nid in stale_nodes:
            self.delete_run(nid, branch=resolved_branch)

        return stale_nodes

    def delete_run(self, node_id: str, branch: str | None = None) -> bool:
        """Deletes recorded run output for a specific test node ID on the active git branch."""
        resolved_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM test_runs WHERE branch = ? AND (node_id = ? OR node_id LIKE ?)",
                (resolved_branch, node_id, f"%{node_id}"),
            )
            conn.commit()

            return cur.rowcount > 0

    def clear_runs(self) -> int:
        """Clears all stored test run records."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM test_runs")
            conn.commit()
            return cur.rowcount

    def prune_orphans(
        self, valid_node_ids: list[str], branch: str | None = None
    ) -> int:
        """Deletes any stored runs on the active git branch whose node_id is no longer present in the valid test list."""
        if not valid_node_ids:
            return 0
        resolved_branch = self.get_current_branch() if branch is None else branch
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT node_id FROM test_runs WHERE branch = ?",
                (resolved_branch,),
            )
            existing_ids = [row["node_id"] for row in cur.fetchall()]

            # Determine orphans by exact and suffix match
            orphans = [
                eid
                for eid in existing_ids
                if not any(
                    eid == vid or eid.endswith(vid) or vid.endswith(eid)
                    for vid in valid_node_ids
                )
            ]

            if not orphans:
                return 0

            placeholders = ",".join(["?"] * len(orphans))
            del_cur = conn.execute(
                f"DELETE FROM test_runs WHERE branch = ? AND node_id IN ({placeholders})",
                [resolved_branch, *orphans],
            )
            conn.commit()
            return del_cur.rowcount

    def get_stored_branches(self) -> list[str]:
        """Returns a sorted list of distinct non-empty branch names stored in test_runs."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT DISTINCT branch FROM test_runs WHERE branch != '' ORDER BY branch ASC"
            )
            return [row["branch"] for row in cur.fetchall() if row["branch"]]

    def prune_branches(
        self,
        target_path: str | Path | None = None,
        branches: list[str] | None = None,
    ) -> dict[str, Any]:
        """Deletes test run records belonging to merged or deleted local git branches.

        Protects the active branch, trunk branches ('main', 'master', 'develop'),
        and non-git runs (''). Returns the list of pruned branch names and deleted row count.
        """
        effective_target = target_path if target_path is not None else self.target_path
        if branches is None:
            stored_branches = self.get_stored_branches()
            if not stored_branches:
                return {"branches": [], "deleted_count": 0}
            target_branches = get_prunable_git_branches(
                effective_target, stored_branches
            )
        else:
            target_branches = sorted({b for b in branches if b})

        if not target_branches:
            return {"branches": [], "deleted_count": 0}

        placeholders = ",".join(["?"] * len(target_branches))
        with self._get_connection() as conn:
            del_cur = conn.execute(
                f"DELETE FROM test_runs WHERE branch IN ({placeholders})",
                target_branches,
            )
            conn.commit()
            return {
                "branches": target_branches,
                "deleted_count": del_cur.rowcount,
            }


    def save_run_options(
        self,
        marker_filter: str = "",
        extra_args: str = "",
        suite: str = "unit",
    ) -> None:
        """Saves run options (marker filter and extra args) for the specified suite slot."""
        slot = normalize_suite_slot(suite)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO run_options (suite, marker_filter, extra_args, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(suite) DO UPDATE SET
                    marker_filter=excluded.marker_filter,
                    extra_args=excluded.extra_args,
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (slot, marker_filter or "", extra_args or ""),
            )
            conn.commit()

    def get_run_options(self, suite: str = "unit") -> dict[str, str]:
        """Retrieves stored run options (marker filter and extra args) for the specified suite slot."""
        slot = normalize_suite_slot(suite)
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT marker_filter, extra_args FROM run_options WHERE suite = ?",
                (slot,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "marker_filter": row["marker_filter"] or "",
                    "extra_args": row["extra_args"] or "",
                }
            return {"marker_filter": "", "extra_args": ""}

    def get_all_run_options(self) -> dict[str, dict[str, str]]:
        """Retrieves stored run options for all three suite slots ('unit', 'integration', 'acceptance')."""
        result: dict[str, dict[str, str]] = {
            slot: {"marker_filter": "", "extra_args": ""} for slot in SUITE_SLOTS
        }
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT suite, marker_filter, extra_args FROM run_options"
            )
            for row in cur.fetchall():
                slot = normalize_suite_slot(row["suite"])
                result[slot] = {
                    "marker_filter": row["marker_filter"] or "",
                    "extra_args": row["extra_args"] or "",
                }
        return result

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
        name = str(env_data.get("name") or "Default Environment").strip() or "Default Environment"
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
        name = str(node_data.get("name") or ("New Group" if node_type == "group" else "New Request")).strip()
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
        create_group_with_node_id: str | None = None,
        group_name: str | None = None,
    ) -> dict[str, Any]:
        """Moves an API node to a new parent/order or groups it with another node via drag-and-drop."""
        with self._get_connection() as conn:
            if create_group_with_node_id and create_group_with_node_id != node_id:
                target_row = conn.execute(
                    "SELECT id, parent_id, sort_order, name FROM api_nodes WHERE id = ?",
                    (create_group_with_node_id,),
                ).fetchone()
                if target_row:
                    new_group_id = f"grp-{uuid.uuid4().hex[:8]}"
                    g_name = (group_name or f"{target_row['name']} Group").strip()
                    conn.execute(
                        """
                        INSERT INTO api_nodes (id, parent_id, node_type, name, sort_order, method, path, updated_at)
                        VALUES (?, ?, 'group', ?, ?, 'GET', '', CURRENT_TIMESTAMP)
                        """,
                        (
                            new_group_id,
                            target_row["parent_id"],
                            g_name,
                            int(target_row["sort_order"] or 0),
                        ),
                    )
                    conn.execute(
                        "UPDATE api_nodes SET parent_id = ?, sort_order = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_group_id, create_group_with_node_id),
                    )
                    conn.execute(
                        "UPDATE api_nodes SET parent_id = ?, sort_order = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_group_id, node_id),
                    )
                    conn.commit()
                    return {"group_id": new_group_id, "nodes": self.list_api_nodes()}

            # Standard move / reorder under target_parent_id
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


