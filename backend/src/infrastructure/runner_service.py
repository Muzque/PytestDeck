import asyncio
import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from pathlib import Path

from domain.models import BehaveConfig, PytestConfig, RunnerType
from domain.services import is_safe_subpath
from infrastructure.env_status import apply_target_venv, ensure_target_env_ready

logger = logging.getLogger(__name__)
PYTESTDECK_EVENT_PATTERN = re.compile(r"__PYTESTDECK_EVENT__:(\{[^\r\n]+\})\r?\n?")
DEFAULT_STREAM_LIMIT = 1024 * 1024  # 1 MB


async def _read_stream_line(stream: asyncio.StreamReader) -> bytes:
    """Reads a line from an asyncio StreamReader, draining gracefully if the buffer limit is exceeded."""
    readuntil_fn = getattr(stream, "readuntil", None)
    if callable(readuntil_fn):
        try:
            return await readuntil_fn(b"\n")
        except asyncio.IncompleteReadError as exc:
            return exc.partial
        except asyncio.LimitOverrunError as exc:
            return await stream.read(max(exc.consumed, 1))
        except ValueError:
            return await stream.read(65536)
    try:
        return await stream.readline()
    except (asyncio.LimitOverrunError, ValueError):
        return await stream.read(65536)




class SubprocessRunnerService:
    """Infrastructure service executing and streaming test process output via asyncio subprocesses.

    Attributes:
        target_path: Resolved Path object pointing to target project directory.
        proc: Active asyncio subprocess handle or None if not running.
    """

    def __init__(self, target_path: str, heartbeat_interval: float = 15.0):
        """Initializes the SubprocessRunnerService instance.

        Args:
            target_path: Absolute directory path of target repository.
            heartbeat_interval: Interval in seconds between server-side ping heartbeats while waiting for stdout.
        """
        self.target_path = Path(target_path).resolve()
        self.proc: asyncio.subprocess.Process | None = None
        self.heartbeat_interval = heartbeat_interval

    def detect_runner_type(self, nodes: list[str] | None = None) -> RunnerType:
        """Determines the appropriate test runner framework type based on target nodes.

        Args:
            nodes: Optional list of test node paths or nodeids to execute.

        Returns:
            RunnerType: BEHAVE if nodes reference feature files or acceptance suite, PYTEST otherwise.
        """
        if nodes and any("acceptance" in n or n.endswith(".feature") for n in nodes):
            return RunnerType.BEHAVE
        return RunnerType.PYTEST

    async def run_test_stream(
        self,
        nodes: list[str] | None = None,
        marker: str | None = None,
        extra_args: list[str] | None = None,
        report_json_path: str | None = None,
        runner_type: RunnerType | None = None,
    ) -> AsyncGenerator[str, None]:
        """Executes test runner in a subprocess and streams output lines asynchronously.

        Args:
            nodes: Optional list of test node paths/nodeids to execute.
            marker: Optional pytest marker filter expression (e.g. -m smoke).
            extra_args: Optional additional command line arguments.
            report_json_path: Optional temporary file path to generate JSON report.
            runner_type: Explicit RunnerType enum (PYTEST or BEHAVE). Auto-detected if None.

        Yields:
            AsyncGenerator[str, None]: JSON-serialized streaming message chunks (status, stdout, finished).
        """
        ensure_target_env_ready()

        if nodes:
            for node in nodes:
                if not is_safe_subpath(self.target_path, node):
                    raise ValueError(f"Unsafe node path traversal detected: {node}")

        resolved_runner_type = runner_type or self.detect_runner_type(nodes)
        if resolved_runner_type == RunnerType.BEHAVE:
            exec_config = BehaveConfig(
                nodes=nodes or [],
                extra_args=extra_args or [],
            )
        else:
            exec_config = PytestConfig(
                nodes=nodes or [],
                marker=marker,
                extra_args=extra_args or [],
                report_json_path=report_json_path,
            )
        cmd = exec_config.build_command()

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["PY_COLORS"] = "1"
        env["FORCE_COLOR"] = "1"
        apply_target_venv(env)

        # Ensure target repository root, target src (if exists), and PytestDeck backend/src are on PYTHONPATH
        src_paths = [str(self.target_path)]
        target_src = (self.target_path / "src").resolve()
        if target_src.is_dir() and str(target_src) not in src_paths:
            src_paths.append(str(target_src))
        backend_src = str(Path(__file__).parent.parent.resolve())
        if backend_src not in src_paths:
            src_paths.append(backend_src)
        existing_pythonpath = env.get("PYTHONPATH", "")
        if existing_pythonpath:
            src_paths.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(src_paths)

        if resolved_runner_type == RunnerType.PYTEST:
            existing_addopts = env.get("PYTEST_ADDOPTS", "").strip()
            plugin_flag = "-p infrastructure.pytest_status_plugin"
            if plugin_flag not in existing_addopts:
                env["PYTEST_ADDOPTS"] = (
                    f"{existing_addopts} {plugin_flag}".strip()
                )


        from infrastructure.output_splitter import MethodOutputCollector
        from infrastructure.storage_service import get_target_git_branch

        run_branch = get_target_git_branch(self.target_path)
        output_collector = MethodOutputCollector(requested_nodes=nodes)

        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.target_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            start_new_session=True,
            limit=DEFAULT_STREAM_LIMIT,
        )

        yield json.dumps(
            {"type": "status", "data": f"Started process: {' '.join(cmd)}\r\n"}
        )

        if self.proc.stdout:
            read_task: asyncio.Task[bytes] | None = None
            try:
                while True:
                    if read_task is None:
                        read_task = asyncio.create_task(_read_stream_line(self.proc.stdout))
                    done, _ = await asyncio.wait(
                        {read_task}, timeout=self.heartbeat_interval
                    )
                    if not done:
                        yield json.dumps({"type": "ping"})
                        continue
                    line = read_task.result()
                    read_task = None
                    if not line:
                        break
                    line_str = line.decode("utf-8", errors="replace")
                    if "__PYTESTDECK_EVENT__:" in line_str:
                        for match in PYTESTDECK_EVENT_PATTERN.finditer(line_str):
                            try:
                                ev = json.loads(match.group(1))
                                ev_node_id = ev.get("node_id", "")
                                ev_outcome = ev.get("outcome", "")
                                ev_duration = ev.get("duration")
                                if ev_node_id and ev_outcome:
                                    output_collector.record_status_event(
                                        ev_node_id, ev_outcome, ev_duration
                                    )
                                    yield json.dumps(
                                        {
                                            "type": "test_status",
                                            "node_id": ev_node_id,
                                            "outcome": ev_outcome,
                                            "duration": ev_duration,
                                        }
                                    )
                            except Exception:
                                pass
                        cleaned_line = PYTESTDECK_EVENT_PATTERN.sub("", line_str)
                        if not cleaned_line.strip():
                            continue
                        line_str = cleaned_line

                    output_collector.process_line(line_str)
                    yield json.dumps({"type": "stdout", "data": line_str})
            finally:
                if read_task is not None and not read_task.done():
                    read_task.cancel()


        exit_code = await self.proc.wait()

        summary = {"exit_code": exit_code}
        if report_json_path and Path(report_json_path).exists():
            try:
                with open(report_json_path, "r", encoding="utf-8") as f:
                    summary["report"] = json.load(f)
                    output_collector.merge_json_report(summary["report"])
            except Exception as e:
                summary["report_error"] = str(e)

        method_outputs = output_collector.get_results()

        if "report" not in summary and "report_error" not in summary and method_outputs:
            passed_count = sum(
                1 for r in method_outputs.values() if r.get("outcome") == "passed"
            )
            failed_count = sum(
                1
                for r in method_outputs.values()
                if r.get("outcome") in ("failed", "error")
            )
            skipped_count = sum(
                1 for r in method_outputs.values() if r.get("outcome") == "skipped"
            )
            total_count = passed_count + failed_count + skipped_count
            summary["report"] = {
                "summary": {
                    "total": total_count,
                    "passed": passed_count,
                    "failed": failed_count,
                    "skipped": skipped_count,
                }
            }

        # Persist method outputs to SQLite database with branch, code_hash, file_hash, and file_mtime
        try:
            from infrastructure.history_db import HistoryDatabase
            from infrastructure.test_detail_service import (
                compute_file_hash,
                get_node_code_metadata,
                resolve_test_file,
            )

            db = HistoryDatabase(target_path=self.target_path)
            file_hash_cache: dict[str, str | None] = {}
            metadata_cache: dict[str, object] = {}
            for nid, record in method_outputs.items():
                code_hash, file_mtime = get_node_code_metadata(
                    self.target_path, nid, cache=metadata_cache
                )
                rel_file = nid.split("::")[0]
                if rel_file not in file_hash_cache:
                    full_path = resolve_test_file(Path(self.target_path), rel_file)
                    file_hash_cache[rel_file] = (
                        compute_file_hash(full_path) if full_path else None
                    )
                record["branch"] = run_branch
                record["code_hash"] = code_hash
                record["file_mtime"] = file_mtime
                record["file_hash"] = file_hash_cache[rel_file]
            db.save_runs(method_outputs, branch=run_branch)
        except Exception as exc:
            logger.warning(
                "Failed to persist test run history for %s: %s",
                self.target_path,
                exc,
            )

        yield json.dumps(
            {
                "type": "finished",
                "exit_code": exit_code,
                "summary": summary,
                "method_outputs": method_outputs,
                "branch": run_branch,
            }
        )

    async def abort(self) -> None:
        """Aborts the currently running subprocess execution cleanly."""
        if self.proc and self.proc.returncode is None:
            try:
                pgid = None
                if hasattr(os, "getpgid"):
                    try:
                        child_pgid = os.getpgid(self.proc.pid)
                        current_pgid = os.getpgid(0)
                        if child_pgid != current_pgid:
                            pgid = child_pgid
                    except (ProcessLookupError, OSError):
                        pass

                if pgid and hasattr(os, "killpg"):
                    import signal

                    os.killpg(pgid, signal.SIGTERM)
                else:
                    self.proc.terminate()

                wait_fn = getattr(self.proc, "wait", None)
                if callable(wait_fn):
                    try:
                        res = wait_fn()
                        if asyncio.iscoroutine(res):
                            await asyncio.wait_for(res, timeout=0.5)
                        else:
                            await asyncio.sleep(0.5)
                    except TimeoutError:
                        pass
                else:
                    await asyncio.sleep(0.5)

                if self.proc.returncode is None:
                    if pgid and hasattr(os, "killpg"):
                        import signal

                        os.killpg(pgid, signal.SIGKILL)
                    else:
                        self.proc.kill()
                    if callable(wait_fn):
                        try:
                            res2 = wait_fn()
                            if asyncio.iscoroutine(res2):
                                await asyncio.wait_for(res2, timeout=0.5)
                        except TimeoutError:
                            pass
            except (ProcessLookupError, OSError):
                pass
