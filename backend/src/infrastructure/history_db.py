import datetime
import os
import sqlite3
from pathlib import Path
from typing import Any

from infrastructure.storage_service import get_target_storage_dir


class HistoryDatabase:
    """Manages SQLite persistence for individual test method run outputs, durations, outcomes, and code hashes."""

    def __init__(
        self, target_path: str | Path | None = None, db_path: str | Path | None = None
    ):
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
        self._init_db()

    def _ensure_storage_dir(self) -> None:
        """Ensures parent directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates the test_runs table and indexes if they do not exist."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    node_id TEXT PRIMARY KEY,
                    outcome TEXT,
                    duration REAL,
                    timestamp TEXT,
                    output TEXT,
                    code_hash TEXT,
                    file_mtime REAL,
                    file_hash TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            # Ensure file_hash column exists on existing databases
            try:
                conn.execute("ALTER TABLE test_runs ADD COLUMN file_hash TEXT;")
            except sqlite3.OperationalError:
                pass

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_runs_updated ON test_runs(updated_at);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_options (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    marker_filter TEXT,
                    extra_args TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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
    ) -> None:
        """Saves or updates a test method's execution record."""
        now_ts = timestamp or datetime.datetime.now(datetime.UTC).strftime(
            "%H:%M:%S UTC"
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_runs (node_id, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(node_id) DO UPDATE SET
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

    def save_runs(self, runs: dict[str, dict[str, Any]]) -> None:
        """Batch saves multiple test method execution outputs."""
        if not runs:
            return
        with self._get_connection() as conn:
            for node_id, data in runs.items():
                conn.execute(
                    """
                    INSERT INTO test_runs (node_id, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(node_id) DO UPDATE SET
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

    def get_run(self, node_id: str) -> dict[str, Any] | None:
        """Fetches the latest run details for a given test node ID."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT node_id, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs WHERE node_id = ?",
                (node_id,),
            )
            row = cur.fetchone()
            if row:
                return dict(row)

            # Suffix match fallback (in case relative path prefix differs)
            cur = conn.execute(
                "SELECT node_id, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs WHERE node_id LIKE ? LIMIT 1",
                (f"%{node_id}",),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_runs(self) -> dict[str, dict[str, Any]]:
        """Returns all recorded test runs indexed by node_id."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT node_id, outcome, duration, timestamp, output, code_hash, file_mtime, file_hash FROM test_runs ORDER BY updated_at DESC"
            )
            return {row["node_id"]: dict(row) for row in cur.fetchall()}

    def clean_stale_runs(self, target_path: str | Path | None = None) -> list[str]:
        """Checks stored runs against target repo files and purges stale/modified records.

        If a test file is missing or its content/hash has been modified since the run was recorded,
        the run is deleted from the database.
        Returns a list of node_ids that were removed.
        """
        if not target_path:
            return []
        try:
            from domain.services import resolve_target_path
            from infrastructure.test_detail_service import (
                compute_file_hash,
                get_node_code_metadata,
                resolve_test_file,
            )

            target_dir = resolve_target_path(str(target_path))
        except Exception:
            return []

        all_runs = self.get_all_runs()
        if not all_runs:
            return []

        stale_nodes: list[str] = []
        file_hash_cache: dict[str, str | None] = {}

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
                curr_code_hash, _ = get_node_code_metadata(target_dir, node_id)
                if curr_code_hash != stored_code_hash:
                    stale_nodes.append(node_id)
            else:
                stored_mtime = data.get("file_mtime")
                if stored_mtime:
                    _, curr_mtime = get_node_code_metadata(target_dir, node_id)
                    if curr_mtime and curr_mtime > stored_mtime + 1.0:
                        stale_nodes.append(node_id)

        for nid in stale_nodes:
            self.delete_run(nid)

        return stale_nodes

    def delete_run(self, node_id: str) -> bool:
        """Deletes recorded run output for a specific test node ID."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "DELETE FROM test_runs WHERE node_id = ? OR node_id LIKE ?",
                (node_id, f"%{node_id}"),
            )
            conn.commit()

            return cur.rowcount > 0

    def clear_runs(self) -> int:
        """Clears all stored test run records."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM test_runs")
            conn.commit()
            return cur.rowcount

    def prune_orphans(self, valid_node_ids: list[str]) -> int:
        """Deletes any stored runs whose node_id is no longer present in the valid test list."""
        if not valid_node_ids:
            return 0
        with self._get_connection() as conn:
            cur = conn.execute("SELECT node_id FROM test_runs")
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
                f"DELETE FROM test_runs WHERE node_id IN ({placeholders})", orphans
            )
            conn.commit()
            return del_cur.rowcount

    def save_run_options(self, marker_filter: str = "", extra_args: str = "") -> None:
        """Saves run options (marker filter and extra args) to the database."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO run_options (id, marker_filter, extra_args, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    marker_filter=excluded.marker_filter,
                    extra_args=excluded.extra_args,
                    updated_at=CURRENT_TIMESTAMP;
                """,
                (marker_filter or "", extra_args or ""),
            )
            conn.commit()

    def get_run_options(self) -> dict[str, str]:
        """Retrieves stored run options (marker filter and extra args)."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT marker_filter, extra_args FROM run_options WHERE id = 1"
            )
            row = cur.fetchone()
            if row:
                return {
                    "marker_filter": row["marker_filter"] or "",
                    "extra_args": row["extra_args"] or "",
                }
            return {"marker_filter": "", "extra_args": ""}
