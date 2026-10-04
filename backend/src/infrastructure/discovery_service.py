import asyncio
import json
import os
import tempfile
from typing import Any

from infrastructure.env_status import apply_target_venv, ensure_target_env_ready


def get_env_config() -> dict[str, Any]:
    """Retrieves PytestDeck configuration values from environment variables.

    Returns:
        dict[str, Any]: Dictionary containing configured suite paths and environment settings.
    """
    return {
        "unit_dir": os.getenv("UNIT_DIR", "backend/tests/unit"),
        "integration_dir": os.getenv("INTEGRATION_DIR", "backend/tests/integration"),
        "acceptance_dir": os.getenv("ACCEPTANCE_DIR", "backend/tests/acceptance"),
    }


class PytestDiscoveryService:
    """Infrastructure service executing pytest collect-only process."""

    async def collect_raw(self, target_path: str, suite_rel_path: str = "") -> tuple[list[dict[str, Any]], int]:
        """Executes a subprocess collect-only pytest pass on the target directory.

        Args:
            target_path: Absolute directory path of the target Python repository.
            suite_rel_path: Relative directory path of the specific test suite.

        Returns:
            tuple[list[dict[str, Any]], int]: Raw JSON collectors list and total test item count.

        Raises:
            ValueError: If target_path does not exist or is not a directory.
        """
        from domain.services import resolve_target_path

        target_dir = resolve_target_path(target_path)
        ensure_target_env_ready()

        # Handle Behave feature files discovery if suite is acceptance
        if "acceptance" in suite_rel_path or suite_rel_path.endswith(".feature"):
            from infrastructure.test_detail_service import parse_gherkin_scenarios

            suite_dir = target_dir / suite_rel_path if suite_rel_path else target_dir
            collectors = []
            if suite_dir.exists():
                feature_files = sorted(suite_dir.rglob("*.feature"))
                for feat in feature_files:
                    rel_feat_path = str(feat.relative_to(target_dir))
                    scenarios = parse_gherkin_scenarios(feat)
                    if scenarios:
                        results = [
                            {
                                "nodeid": f"{rel_feat_path}::{sc['title']}",
                                "type": "Function",
                                "lineno": sc["line"],
                            }
                            for sc in scenarios
                        ]
                    else:
                        results = [{
                            "nodeid": rel_feat_path,
                            "type": "Function",
                            "lineno": 1,
                        }]
                    collectors.append({
                        "nodeid": rel_feat_path,
                        "result": results,
                    })
            total_items = sum(len(c.get("result", [])) for c in collectors)
            return collectors, total_items

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_report = tmp.name

        try:
            cmd = [
                "uv", "run", "--with", "pytest-json-report", "pytest", "--collect-only",
                "--json-report", f"--json-report-file={tmp_report}",
                "--disable-warnings"
            ]

            if suite_rel_path:
                ini_path = target_dir / suite_rel_path / "pytest.ini"
                if not ini_path.exists():
                    ini_path = target_dir / "pytest.ini"
                if ini_path.exists():
                    cmd.extend(["-c", str(ini_path)])
                cmd.append(suite_rel_path)

            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            apply_target_venv(env)

            src_paths = [str(target_dir)]
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                src_paths.append(existing_pythonpath)
            env["PYTHONPATH"] = os.pathsep.join(src_paths)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(target_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()

            collectors = []
            if os.path.exists(tmp_report):
                try:
                    with open(tmp_report, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                        collectors = report_data.get("collectors", [])
                except Exception:
                    pass

            if not collectors and proc.returncode not in (0, 5):
                err_msg = stderr_bytes.decode("utf-8", errors="replace").strip() or stdout_bytes.decode("utf-8", errors="replace").strip()
                if err_msg:
                    raise ValueError(f"Pytest test collection failed:\n{err_msg}")

            total_items = sum(
                1 for c in collectors for r in c.get("result", [])
                if r.get("type") in ("Function", "Item", "TestCase")
            )
            return collectors, total_items
        finally:
            if os.path.exists(tmp_report):
                try:
                    os.remove(tmp_report)
                except OSError:
                    pass
