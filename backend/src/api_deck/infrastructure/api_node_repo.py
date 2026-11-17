import json
import sqlite3
import uuid
from collections.abc import Callable
from typing import Any

from api_deck.infrastructure.api_environment_repo import ApiEnvironmentRepository


class ApiNodeRepository:
    """Handles SQLite persistence for API Deck groups, requests, ordering, and run status."""

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

    def row_to_api_node(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "environment_id": row["environment_id"] or "",
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

    def list_api_nodes(self, environment_id: str | None = None) -> list[dict[str, Any]]:
        """Returns API request and group nodes for the active (or specified) environment ordered by sort_order and rowid."""
        with self._get_connection() as conn:
            env_id = (
                environment_id
                if environment_id is not None
                else ApiEnvironmentRepository.get_active_environment_id(conn)
            )
            if not env_id:
                return []
            cur = conn.execute(
                """
                SELECT id, environment_id, parent_id, node_type, name, sort_order, method, path,
                       query_params, headers, body_type, body, expected_status,
                       last_status, last_duration_ms, last_outcome, last_response_meta
                FROM api_nodes
                WHERE environment_id = ?
                ORDER BY sort_order ASC, rowid ASC
                """,
                (env_id,),
            )
            return [self.row_to_api_node(r) for r in cur.fetchall()]

    def upsert_api_node(
        self, node_data: dict[str, Any], environment_id: str | None = None
    ) -> dict[str, Any]:
        """Inserts or updates an API group or request node within its environment."""
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
        req_env_id = (
            str(environment_id or node_data.get("environment_id") or "").strip() or None
        )

        with self._get_connection() as conn:
            active_env_id = ApiEnvironmentRepository.ensure_active_environment_id(
                conn, req_env_id
            )
            existing = conn.execute(
                "SELECT environment_id, sort_order, parent_id FROM api_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()
            if existing is not None:
                existing_env_id = str(existing["environment_id"] or "")
                if existing_env_id:
                    if req_env_id and req_env_id != existing_env_id:
                        raise ValueError("Cannot move node across environments")
                    if not req_env_id and existing_env_id != active_env_id:
                        raise ValueError("Node belongs to a different environment")
                    target_env_id = existing_env_id
                else:
                    target_env_id = req_env_id or active_env_id
            else:
                target_env_id = ApiEnvironmentRepository.ensure_active_environment_id(
                    conn, req_env_id or active_env_id
                )

            if "parent_id" not in node_data and existing is not None:
                parent_id = existing["parent_id"]

            if parent_id is not None:
                parent_row = conn.execute(
                    "SELECT id, environment_id FROM api_nodes WHERE id = ?",
                    (parent_id,),
                ).fetchone()
                if (
                    parent_row is None
                    or str(parent_row["environment_id"] or "") != target_env_id
                ):
                    raise ValueError(
                        "Parent node does not belong to the target environment"
                    )

            if "sort_order" in node_data and node_data["sort_order"] is not None:
                sort_order = int(node_data["sort_order"])
            elif existing is not None:
                sort_order = int(existing["sort_order"] or 0)
            else:
                max_row = conn.execute(
                    """
                    SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order
                    FROM api_nodes
                    WHERE environment_id = ? AND COALESCE(parent_id, '') = COALESCE(?, '')
                    """,
                    (target_env_id, parent_id),
                ).fetchone()
                sort_order = int(max_row["next_order"] if max_row else 0)

            conn.execute(
                """
                INSERT INTO api_nodes (
                    id, environment_id, parent_id, node_type, name, sort_order, method, path,
                    query_params, headers, body_type, body, expected_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
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
                    target_env_id,
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
                SELECT id, environment_id, parent_id, node_type, name, sort_order, method, path,
                       query_params, headers, body_type, body, expected_status,
                       last_status, last_duration_ms, last_outcome, last_response_meta
                FROM api_nodes WHERE id = ?
                """,
                (node_id,),
            ).fetchone()
            return self.row_to_api_node(row)

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
        with self._get_connection() as conn:
            env_id = (
                environment_id
                if environment_id is not None
                else ApiEnvironmentRepository.get_active_environment_id(conn)
            )
            if env_id:
                conn.execute(
                    """
                    UPDATE api_nodes
                    SET last_status = ?,
                        last_duration_ms = ?,
                        last_outcome = ?,
                        last_response_meta = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND environment_id = ?
                    """,
                    (
                        status_code,
                        duration_ms,
                        outcome,
                        json.dumps(meta or {}),
                        node_id,
                        env_id,
                    ),
                )
            else:
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
        environment_id: str | None = None,
    ) -> dict[str, Any]:
        """Moves an API node to a new parent and sibling sort order within the same environment."""
        with self._get_connection() as conn:
            active_env_id = (
                environment_id
                if environment_id is not None
                else ApiEnvironmentRepository.get_active_environment_id(conn)
            )
            node_row = conn.execute(
                "SELECT id, environment_id FROM api_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()
            if node_row is None:
                raise ValueError("Node not found")
            env_id = str(node_row["environment_id"] or "")
            if active_env_id and env_id != active_env_id:
                raise ValueError("Node does not belong to the active environment")

            if target_parent_id is not None:
                parent_row = conn.execute(
                    "SELECT id, environment_id FROM api_nodes WHERE id = ?",
                    (target_parent_id,),
                ).fetchone()
                if (
                    parent_row is None
                    or str(parent_row["environment_id"] or "") != env_id
                ):
                    raise ValueError(
                        "Target parent does not belong to the same environment"
                    )

            siblings = conn.execute(
                """
                SELECT id FROM api_nodes
                WHERE environment_id = ? AND COALESCE(parent_id, '') = COALESCE(?, '') AND id != ?
                ORDER BY sort_order ASC, rowid ASC
                """,
                (env_id, target_parent_id, node_id),
            ).fetchall()
            ordered_ids = [r["id"] for r in siblings]
            idx = max(0, min(int(target_index), len(ordered_ids)))
            ordered_ids.insert(idx, node_id)

            conn.execute(
                "UPDATE api_nodes SET parent_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND environment_id = ?",
                (target_parent_id, node_id, env_id),
            )
            for i, sid in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE api_nodes SET sort_order = ? WHERE id = ? AND environment_id = ?",
                    (i, sid, env_id),
                )
            conn.commit()
            return {
                "group_id": None,
                "nodes": self.list_api_nodes(environment_id=env_id),
            }

    def delete_api_node(
        self, node_id: str, environment_id: str | None = None
    ) -> int:
        """Deletes an API node in the active environment and recursively deletes any child nodes if it is a group."""
        with self._get_connection() as conn:
            env_id = (
                environment_id
                if environment_id is not None
                else ApiEnvironmentRepository.get_active_environment_id(conn)
            )
            if not env_id:
                return 0
            root_row = conn.execute(
                "SELECT id FROM api_nodes WHERE id = ? AND environment_id = ?",
                (node_id, env_id),
            ).fetchone()
            if root_row is None:
                return 0
            to_delete = [node_id]
            visited: set[str] = set()
            while to_delete:
                curr = to_delete.pop()
                if curr in visited:
                    continue
                visited.add(curr)
                children = conn.execute(
                    "SELECT id FROM api_nodes WHERE parent_id = ? AND environment_id = ?",
                    (curr, env_id),
                ).fetchall()
                for c in children:
                    to_delete.append(c["id"])

            if not visited:
                return 0
            placeholders = ",".join(["?"] * len(visited))
            cur = conn.execute(
                f"DELETE FROM api_nodes WHERE environment_id = ? AND id IN ({placeholders})",
                [env_id, *list(visited)],
            )
            conn.commit()
            return cur.rowcount
