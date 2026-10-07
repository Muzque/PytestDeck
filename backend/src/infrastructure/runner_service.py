import asyncio
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from domain.models import BehaveConfig, PytestConfig, RunnerType
from domain.services import is_safe_subpath
from infrastructure.env_status import apply_target_venv, ensure_target_env_ready


class SubprocessRunnerService:
    """Infrastructure service executing and streaming test process output via asyncio subprocesses.

    Attributes:
        target_path: Resolved Path object pointing to target project directory.
        proc: Active asyncio subprocess handle or None if not running.
    """

    def __init__(self, target_path: str):
        """Initializes the SubprocessRunnerService instance.

        Args:
            target_path: Absolute directory path of target repository.
        """
        self.target_path = Path(target_path).resolve()
        self.proc: asyncio.subprocess.Process | None = None

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

        # Ensure target repository root is on PYTHONPATH
        src_paths = [str(self.target_path)]
        existing_pythonpath = env.get("PYTHONPATH", "")
        if existing_pythonpath:
            src_paths.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(src_paths)

        from infrastructure.output_splitter import MethodOutputCollector

        output_collector = MethodOutputCollector(requested_nodes=nodes)

        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.target_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

        yield json.dumps(
            {"type": "status", "data": f"Started process: {' '.join(cmd)}\r\n"}
        )

        if self.proc.stdout:
            while True:
                line = await self.proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace")
                output_collector.process_line(line_str)
                yield json.dumps({"type": "stdout", "data": line_str})

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

        # Persist method outputs to SQLite database with code_hash, file_hash, and file_mtime
        try:
            from infrastructure.history_db import HistoryDatabase
            from infrastructure.test_detail_service import (
                compute_file_hash,
                get_node_code_metadata,
                resolve_test_file,
            )

            db = HistoryDatabase(target_path=self.target_path)
            file_hash_cache: dict[str, str | None] = {}
            for nid, record in method_outputs.items():
                code_hash, file_mtime = get_node_code_metadata(self.target_path, nid)
                rel_file = nid.split("::")[0]
                if rel_file not in file_hash_cache:
                    full_path = resolve_test_file(Path(self.target_path), rel_file)
                    file_hash_cache[rel_file] = (
                        compute_file_hash(full_path) if full_path else None
                    )
                record["code_hash"] = code_hash
                record["file_mtime"] = file_mtime
                record["file_hash"] = file_hash_cache[rel_file]
            db.save_runs(method_outputs)
        except Exception:
            pass

        yield json.dumps(
            {
                "type": "finished",
                "exit_code": exit_code,
                "summary": summary,
                "method_outputs": method_outputs,
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

                await asyncio.sleep(0.5)
                if self.proc.returncode is None:
                    if pgid and hasattr(os, "killpg"):
                        import signal

                        os.killpg(pgid, signal.SIGKILL)
                    else:
                        self.proc.kill()
            except (ProcessLookupError, OSError):
                pass
