import json
import sys
from typing import Any

EVENT_PREFIX = "__PYTESTDECK_EVENT__:"


class _PytestDeckStatusReporter:
    """Pytest controller plugin that emits structured per-test lifecycle events for real-time UI updates."""

    def __init__(self) -> None:
        self._durations: dict[str, float] = {}
        self._outcomes: dict[str, str] = {}

    def _emit(self, node_id: str, outcome: str, duration: float | None = None) -> None:
        if not node_id:
            return
        payload = json.dumps(
            {
                "node_id": node_id,
                "outcome": outcome,
                "duration": duration,
            },
            separators=(",", ":"),
        )
        stream = getattr(sys, "__stdout__", None) or sys.stdout
        try:
            stream.write(f"{EVENT_PREFIX}{payload}\n")
            stream.flush()
        except Exception:
            pass

    def pytest_runtest_logstart(
        self, nodeid: str, location: tuple[str, int | None, str]
    ) -> None:
        self._durations[nodeid] = 0.0
        self._emit(nodeid, "running", None)

    def pytest_runtest_logreport(self, report: Any) -> None:
        nodeid = getattr(report, "nodeid", "")
        if not nodeid:
            return
        when = getattr(report, "when", "")
        dur = float(getattr(report, "duration", 0.0) or 0.0)
        self._durations[nodeid] = self._durations.get(nodeid, 0.0) + dur
        total_dur = round(self._durations[nodeid], 4)

        was_xfail = hasattr(report, "wasxfail")
        failed = bool(getattr(report, "failed", False))
        skipped = bool(getattr(report, "skipped", False))

        if when == "setup":
            if failed:
                self._outcomes[nodeid] = "skipped" if was_xfail else "failed"
                self._emit(nodeid, self._outcomes[nodeid], total_dur)
            elif skipped:
                self._outcomes[nodeid] = "skipped"
                self._emit(nodeid, "skipped", total_dur)
        elif when == "call":
            if failed:
                self._outcomes[nodeid] = "skipped" if was_xfail else "failed"
            elif skipped:
                self._outcomes[nodeid] = "skipped"
            else:
                self._outcomes[nodeid] = "passed"
            self._emit(nodeid, self._outcomes[nodeid], total_dur)
        elif when == "teardown":
            if failed and self._outcomes.get(nodeid) != "failed":
                self._outcomes[nodeid] = "failed"
            final_outcome = self._outcomes.get(nodeid, "passed")
            self._emit(nodeid, final_outcome, total_dur)


def pytest_configure(config: Any) -> None:
    if hasattr(config, "workerinput"):
        return
    if not config.pluginmanager.has_plugin("pytestdeck_status_reporter"):
        config.pluginmanager.register(
            _PytestDeckStatusReporter(), "pytestdeck_status_reporter"
        )
