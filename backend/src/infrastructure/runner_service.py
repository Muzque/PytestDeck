import asyncio
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path


class SubprocessRunnerService:
    """Infrastructure service executing and streaming pytest process output via asyncio subprocesses.

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

    async def run_pytest_stream(
        self,
        nodes: list[str] | None = None,
        marker: str | None = None,
        extra_args: list[str] | None = None,
        report_json_path: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Runs pytest in a subprocess and streams stdout lines asynchronously.

        Args:
            nodes: Optional list of test node paths/nodeids to execute.
            marker: Optional pytest marker filter expression (e.g. -m smoke).
            extra_args: Optional additional command line arguments for pytest.
            report_json_path: Optional temporary file path to generate JSON report.

        Yields:
            AsyncGenerator[str, None]: JSON-serialized streaming message chunks (status, stdout, finished).
        """
        is_behave = nodes and any(n.endswith(".feature") for n in nodes)
        if is_behave:
            cmd = ["uv", "run", "behave"]
        else:
            cmd = ["uv", "run", "pytest", "-v", "--color=yes"]

        if not is_behave and report_json_path:
            cmd.extend(["--json-report", f"--json-report-file={report_json_path}"])

        if marker:
            cmd.extend(["-m", marker])

        if extra_args:
            cmd.extend(extra_args)

        if nodes:
            cmd.extend(nodes)

        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"
        env["PY_COLORS"] = "1"
        env["FORCE_COLOR"] = "1"

        self.proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self.target_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )

        yield json.dumps({"type": "status", "data": f"Started process: {' '.join(cmd)}\r\n"})

        if self.proc.stdout:
            while True:
                line = await self.proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace")
                yield json.dumps({"type": "stdout", "data": line_str})

        exit_code = await self.proc.wait()

        summary = {"exit_code": exit_code}
        if report_json_path and Path(report_json_path).exists():
            try:
                with open(report_json_path, "r", encoding="utf-8") as f:
                    summary["report"] = json.load(f)
            except Exception as e:
                summary["report_error"] = str(e)

        yield json.dumps({"type": "finished", "exit_code": exit_code, "summary": summary})

    async def abort(self) -> None:
        """Aborts the currently running subprocess execution cleanly."""
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.terminate()
                await asyncio.sleep(0.5)
                if self.proc.returncode is None:
                    self.proc.kill()
            except ProcessLookupError:
                pass
