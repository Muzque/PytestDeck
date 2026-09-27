import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def parse_pytestdeck_config(config_path: Path) -> dict[str, Any]:
    """Parses the root pytestdeck.toml configuration file.

    Args:
        config_path: Path object pointing to the target pytestdeck.toml file.

    Returns:
        dict[str, Any]: Parsed configuration dictionary under [pytestdeck] section.
    """
    if not config_path.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore

    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    return data.get("pytestdeck", {})


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
        target_dir = Path(target_path).resolve()
        if not target_dir.exists() or not target_dir.is_dir():
            raise ValueError(f"Invalid target path: {target_path}")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_report = tmp.name

        try:
            cmd = [
                "uv", "run", "pytest", "--collect-only",
                "--json-report", f"--json-report-file={tmp_report}",
                "--disable-warnings"
            ]

            if suite_rel_path:
                ini_path = target_dir / suite_rel_path / "pytest.ini"
                if ini_path.exists():
                    cmd.extend(["-c", str(ini_path)])
                cmd.append(suite_rel_path)

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(target_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            collectors = []
            if os.path.exists(tmp_report):
                try:
                    with open(tmp_report, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                        collectors = report_data.get("collectors", [])
                except Exception:
                    pass

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
