import asyncio
import base64
import json
import math
import time
from typing import Any

import httpx


def build_resolved_request(
    node: dict[str, Any], env: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Merges an API request node with the active environment (base_url, auth, default_headers)."""
    env = env or {}
    base_url = str(env.get("base_url") or "").strip().rstrip("/")
    raw_path = str(node.get("path") or "").strip()

    if raw_path.startswith(("http://", "https://")):
        url = raw_path
    elif base_url:
        if raw_path and not raw_path.startswith("/"):
            url = f"{base_url}/{raw_path}"
        else:
            url = f"{base_url}{raw_path}"
    else:
        url = raw_path if raw_path.startswith("/") else f"/{raw_path}"

    headers: dict[str, str] = {}
    for h in env.get("default_headers") or []:
        if isinstance(h, dict) and h.get("enabled", True) and str(h.get("key") or "").strip():
            headers[str(h["key"]).strip()] = str(h.get("value") or "")

    params: dict[str, str] = {}
    for q in node.get("query_params") or []:
        if isinstance(q, dict) and q.get("enabled", True) and str(q.get("key") or "").strip():
            params[str(q["key"]).strip()] = str(q.get("value") or "")

    auth_type = str(env.get("auth_type") or "none").strip().lower()
    auth_cfg = env.get("auth_config") or {}
    if auth_type == "bearer":
        token = str(auth_cfg.get("token") or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        username = str(auth_cfg.get("username") or "")
        password = str(auth_cfg.get("password") or "")
        if username or password:
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
            headers["Authorization"] = f"Basic {encoded}"
    elif auth_type == "api_key":
        key_name = str(auth_cfg.get("key") or "").strip()
        key_val = str(auth_cfg.get("value") or "")
        location = str(auth_cfg.get("in") or "header").strip().lower()
        if key_name:
            if location == "query":
                params[key_name] = key_val
            else:
                headers[key_name] = key_val

    for h in node.get("headers") or []:
        if isinstance(h, dict) and h.get("enabled", True) and str(h.get("key") or "").strip():
            headers[str(h["key"]).strip()] = str(h.get("value") or "")

    method = str(node.get("method") or "GET").strip().upper()
    body_type = str(node.get("body_type") or "json").strip().lower()
    raw_body = str(node.get("body") if node.get("body") is not None else "")
    content: bytes | None = None

    if method not in ("GET", "HEAD") and raw_body:
        content = raw_body.encode("utf-8")
        has_ct = any(k.lower() == "content-type" for k in headers)
        if not has_ct:
            headers["Content-Type"] = (
                "application/json" if body_type == "json" else "text/plain; charset=utf-8"
            )

    expected_status = node.get("expected_status")
    try:
        expected_status_int = int(expected_status) if expected_status else None
    except (TypeError, ValueError):
        expected_status_int = None

    return {
        "method": method,
        "url": url,
        "params": params,
        "headers": headers,
        "content": content,
        "expected_status": expected_status_int,
    }


def _evaluate_outcome(status_code: int | None, expected_status: int | None) -> str:
    if status_code is None:
        return "failed"
    if expected_status is not None and expected_status > 0:
        return "passed" if status_code == expected_status else "failed"
    return "passed" if 200 <= status_code < 300 else "failed"


def _format_response_body(text: str, content_type: str) -> str:
    if not text:
        return ""
    if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            return text
    return text


async def execute_single_request(
    node: dict[str, Any],
    env: dict[str, Any] | None = None,
    timeout_s: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Executes a single HTTP request and returns status, latency, headers, and formatted body."""
    resolved = build_resolved_request(node, env)
    start_ns = time.perf_counter_ns()
    owns_client = client is None
    active_client = client or httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        transport=transport,
    )
    try:
        resp = await active_client.request(
            method=resolved["method"],
            url=resolved["url"],
            params=resolved["params"],
            headers=resolved["headers"],
            content=resolved["content"],
        )
        duration_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 2)
        raw_bytes = resp.content
        size_bytes = len(raw_bytes)
        content_type = resp.headers.get("content-type", "")
        formatted_body = _format_response_body(resp.text, content_type)
        outcome = _evaluate_outcome(resp.status_code, resolved["expected_status"])
        return {
            "node_id": node.get("id"),
            "name": node.get("name"),
            "method": resolved["method"],
            "url": str(resp.request.url),
            "status_code": resp.status_code,
            "duration_ms": duration_ms,
            "size_bytes": size_bytes,
            "headers": dict(resp.headers),
            "body": formatted_body,
            "outcome": outcome,
            "error": None,
        }
    except Exception as exc:
        duration_ms = round((time.perf_counter_ns() - start_ns) / 1_000_000, 2)
        return {
            "node_id": node.get("id"),
            "name": node.get("name"),
            "method": resolved["method"],
            "url": resolved["url"],
            "status_code": None,
            "duration_ms": duration_ms,
            "size_bytes": 0,
            "headers": {},
            "body": f"Request Error: {exc}",
            "outcome": "failed",
            "error": str(exc),
        }
    finally:
        if owns_client:
            await active_client.aclose()


async def execute_batch_requests(
    nodes: list[dict[str, Any]],
    env: dict[str, Any] | None = None,
    concurrency: int = 5,
    timeout_s: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Executes a batch of selected API request nodes and returns individual and aggregate results."""
    req_nodes = [n for n in nodes if n.get("node_type", "request") == "request"]
    if not req_nodes:
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "avg_ms": 0.0,
            "total_ms": 0.0,
            "results": [],
        }

    sem = asyncio.Semaphore(max(1, min(concurrency, 50)))
    batch_start = time.perf_counter_ns()
    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        transport=transport,
    ) as client:
        async def _run_one(item: dict[str, Any]) -> dict[str, Any]:
            async with sem:
                return await execute_single_request(
                    item, env, timeout_s=timeout_s, client=client
                )

        results = await asyncio.gather(*(_run_one(n) for n in req_nodes))

    total_ms = round((time.perf_counter_ns() - batch_start) / 1_000_000, 2)
    passed = sum(1 for r in results if r["outcome"] == "passed")
    failed = len(results) - passed
    durations = [float(r["duration_ms"]) for r in results]
    avg_ms = round(sum(durations) / len(durations), 2) if durations else 0.0

    return {
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "avg_ms": avg_ms,
        "total_ms": total_ms,
        "results": list(results),
    }


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil((pct / 100.0) * len(sorted_vals)) - 1))
    return round(sorted_vals[idx], 2)


async def execute_stress_test(
    node: dict[str, Any],
    env: dict[str, Any] | None = None,
    total_requests: int = 20,
    concurrency: int = 5,
    timeout_s: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Executes parallel requests against an API endpoint and computes Avg, Min, Max, P95 latency."""
    total_n = max(1, min(int(total_requests), 2000))
    conc_c = max(1, min(int(concurrency), min(total_n, 200)))
    resolved = build_resolved_request(node, env)
    sem = asyncio.Semaphore(conc_c)

    latencies: list[float] = []
    status_codes: dict[str, int] = {}
    errors: list[str] = []
    success_count = 0
    fail_count = 0

    limits = httpx.Limits(
        max_connections=conc_c + 10,
        max_keepalive_connections=conc_c,
    )

    wall_start = time.perf_counter_ns()
    async with httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        limits=limits,
        transport=transport,
    ) as client:
        async def _worker(req_idx: int) -> tuple[float, int | None, str, str | None]:
            async with sem:
                t0 = time.perf_counter_ns()
                try:
                    resp = await client.request(
                        method=resolved["method"],
                        url=resolved["url"],
                        params=resolved["params"],
                        headers=resolved["headers"],
                        content=resolved["content"],
                    )
                    dt_ms = round((time.perf_counter_ns() - t0) / 1_000_000, 2)
                    outcome = _evaluate_outcome(
                        resp.status_code, resolved["expected_status"]
                    )
                    return (dt_ms, resp.status_code, outcome, None)
                except Exception as exc:
                    dt_ms = round((time.perf_counter_ns() - t0) / 1_000_000, 2)
                    return (dt_ms, None, "failed", f"Req #{req_idx + 1}: {exc}")

        outcomes = await asyncio.gather(*(_worker(i) for i in range(total_n)))

    wall_ms = max(0.01, round((time.perf_counter_ns() - wall_start) / 1_000_000, 2))

    for dt_ms, sc, outcome, err in outcomes:
        latencies.append(dt_ms)
        key = str(sc) if sc is not None else "ERROR"
        status_codes[key] = status_codes.get(key, 0) + 1
        if outcome == "passed":
            success_count += 1
        else:
            fail_count += 1
        if err and len(errors) < 20:
            errors.append(err)

    sorted_lat = sorted(latencies)
    avg_ms = round(sum(sorted_lat) / len(sorted_lat), 2) if sorted_lat else 0.0
    min_ms = round(sorted_lat[0], 2) if sorted_lat else 0.0
    max_ms = round(sorted_lat[-1], 2) if sorted_lat else 0.0
    p95_ms = _percentile(sorted_lat, 95.0)
    rps = round((total_n / (wall_ms / 1000.0)), 2) if wall_ms > 0 else 0.0

    return {
        "node_id": node.get("id"),
        "name": node.get("name"),
        "method": resolved["method"],
        "url": resolved["url"],
        "total_requests": total_n,
        "concurrency": conc_c,
        "success_count": success_count,
        "fail_count": fail_count,
        "avg_ms": avg_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "p95_ms": p95_ms,
        "wall_time_ms": wall_ms,
        "rps": rps,
        "status_codes": status_codes,
        "errors": errors,
        "latency_samples": latencies[:200],
    }
