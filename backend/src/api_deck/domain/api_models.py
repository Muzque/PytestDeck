from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiEnvironment:
    """Represents a named API server environment configuration (address, auth, default headers)."""

    id: str
    name: str
    base_url: str = ""
    auth_type: str = "none"
    auth_config: dict[str, Any] = field(default_factory=dict)
    default_headers: list[dict[str, Any]] = field(default_factory=list)
    is_active: bool = False


@dataclass
class ApiCollectionNode:
    """Represents either an API folder group or an executable API request node."""

    id: str
    name: str
    node_type: str = "request"
    parent_id: str | None = None
    sort_order: int = 0
    method: str = "GET"
    path: str = ""
    query_params: list[dict[str, Any]] = field(default_factory=list)
    headers: list[dict[str, Any]] = field(default_factory=list)
    body_type: str = "json"
    body: str = ""
    expected_status: int = 200
    last_status: int | None = None
    last_duration_ms: float | None = None
    last_outcome: str | None = None
    last_response_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApiStressResult:
    """Represents the aggregated timing and status metrics from a parallel API stress test."""

    total_requests: int
    concurrency: int
    success_count: int
    fail_count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    rps: float
    warning_count: int = 0
    status_codes: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
