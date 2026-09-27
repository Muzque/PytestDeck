import asyncio
import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path


class SubprocessRunnerService:
    """Infrastructure service to execute and stream pytest process output."""

    def __init__(self, target_path: str):
        self.target_path = Path(target_path).resolve()
        self.proc: asyncio.subprocess.Process | None = None

    async def run_pytest_stream(
        self,
        nodes: list[str] | None = None,
        marker: str | None = None,
        extra_args: list[str] | None = None,
        report_json_path: str | None = None
    ) -> AsyncGenerator[str, None]:
        cmd = ["uv", "run", "pytest", "-v", "--color=yes"]

        if report_json_path:
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
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.terminate()
                await asyncio.sleep(0.5)
                if self.proc.returncode is None:
                    self.proc.kill()
            except ProcessLookupError:
                pass
