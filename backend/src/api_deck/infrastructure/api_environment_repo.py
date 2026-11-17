import json
import sqlite3
import uuid
from collections.abc import Callable
from typing import Any


class ApiEnvironmentRepository:
    """Handles SQLite persistence for API Deck environments and active environment selection."""

    def __init__(self, get_connection: Callable[[], sqlite3.Connection]):
        self._get_connection = get_connection

    @staticmethod
    def _parse_json_field(raw: str | None, default: Any) -> Any:
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    def row_to_api_env(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "base_url": row["base_url"] or "",
            "auth_type": row["auth_type"] or "none",
            "auth_config": self._parse_json_field(row["auth_config"], {}),
            "default_headers": self._parse_json_field(row["default_headers"], []),
            "is_active": bool(row["is_active"]),
        }

    @staticmethod
    def get_active_environment_id(conn: sqlite3.Connection) -> str | None:
        active_row = conn.execute(
            "SELECT id FROM api_environments WHERE is_active = 1 ORDER BY rowid ASC LIMIT 1"
        ).fetchone()
        if active_row:
            return str(active_row["id"])
        first_row = conn.execute(
            "SELECT id FROM api_environments ORDER BY rowid ASC LIMIT 1"
        ).fetchone()
        return str(first_row["id"]) if first_row else None

    @staticmethod
    def ensure_active_environment_id(
        conn: sqlite3.Connection, preferred_env_id: str | None = None
    ) -> str:
        if preferred_env_id:
            pref_row = conn.execute(
                "SELECT id FROM api_environments WHERE id = ?", (preferred_env_id,)
            ).fetchone()
            if pref_row:
                return str(pref_row["id"])

        active_row = conn.execute(
            "SELECT id FROM api_environments WHERE is_active = 1 ORDER BY rowid ASC LIMIT 1"
        ).fetchone()
        if active_row:
            return str(active_row["id"])

        first_row = conn.execute(
            "SELECT id FROM api_environments ORDER BY rowid ASC LIMIT 1"
        ).fetchone()
        if first_row:
            env_id = str(first_row["id"])
            conn.execute(
                "UPDATE api_environments SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (env_id,),
            )
            return env_id

        default_id = f"env-{uuid.uuid4().hex[:8]}"
        conn.execute(
            """
            INSERT INTO api_environments (
                id, name, base_url, auth_type, auth_config, default_headers, is_active, updated_at
            )
            VALUES (?, 'Default Environment', 'http://127.0.0.1:9388', 'none', '{}', '[]', 1, CURRENT_TIMESTAMP)
            """,
            (default_id,),
        )
        return default_id

    def list_api_environments(self) -> list[dict[str, Any]]:
        """Returns all saved API server environments ordered by creation/update."""
        with self._get_connection() as conn:
            cur = conn.execute(
                "SELECT id, name, base_url, auth_type, auth_config, default_headers, is_active FROM api_environments ORDER BY rowid ASC"
            )
            return [self.row_to_api_env(r) for r in cur.fetchall()]

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
            return self.row_to_api_env(row)

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
        """Deletes an API environment by ID, cascade-deleting its nodes and activating the next environment if needed."""
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT id, is_active FROM api_environments WHERE id = ?", (env_id,)
            ).fetchone()
            if existing is None:
                return False
            conn.execute("DELETE FROM api_nodes WHERE environment_id = ?", (env_id,))
            cur = conn.execute("DELETE FROM api_environments WHERE id = ?", (env_id,))
            active_left = conn.execute(
                "SELECT id FROM api_environments WHERE is_active = 1 LIMIT 1"
            ).fetchone()
            if active_left is None:
                next_env = conn.execute(
                    "SELECT id FROM api_environments ORDER BY rowid ASC LIMIT 1"
                ).fetchone()
                if next_env is not None:
                    conn.execute(
                        "UPDATE api_environments SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (next_env["id"],),
                    )
            conn.commit()
            return cur.rowcount > 0
