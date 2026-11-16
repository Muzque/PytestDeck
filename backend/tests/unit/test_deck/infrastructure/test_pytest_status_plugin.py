import io
import json
import sys
from types import SimpleNamespace

import infrastructure.pytest_status_plugin as plugin


def test_pytest_status_plugin_emits_running_and_outcome(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "__stdout__", buf)

    reporter = plugin._PytestDeckStatusReporter()
    nodeid = "tests/unit/test_sample.py::test_alpha"
    reporter.pytest_runtest_logstart(
        nodeid=nodeid, location=("test_sample.py", 1, "test_alpha")
    )

    report = SimpleNamespace(
        when="call",
        nodeid=nodeid,
        failed=False,
        skipped=False,
        duration=0.015,
    )
    reporter.pytest_runtest_logreport(report)

    lines = [
        line
        for line in buf.getvalue().splitlines()
        if plugin.EVENT_PREFIX in line
    ]
    assert len(lines) == 2
    first_payload = json.loads(lines[0].split(plugin.EVENT_PREFIX, 1)[1])
    second_payload = json.loads(lines[1].split(plugin.EVENT_PREFIX, 1)[1])
    assert first_payload["node_id"] == nodeid
    assert first_payload["outcome"] == "running"
    assert second_payload["node_id"] == nodeid
    assert second_payload["outcome"] == "passed"
