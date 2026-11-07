import pytest

from infrastructure.runner_service import SubprocessRunnerService


@pytest.mark.anyio
async def test_subprocess_runner_service_init(tmp_path):
    runner = SubprocessRunnerService(str(tmp_path))
    assert runner.target_path == tmp_path.resolve()
    assert runner.proc is None


@pytest.mark.anyio
async def test_subprocess_runner_service_stream(tmp_path):
    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_dummy.py"
    test_file.write_text("def test_dummy_pass(): assert True\n", encoding="utf-8")

    runner = SubprocessRunnerService(str(tmp_path))
    chunks = []
    async for chunk in runner.run_test_stream(nodes=["tests/test_dummy.py"]):
        chunks.append(chunk)


    assert len(chunks) > 0
    assert any("Started process" in c for c in chunks)
    assert any("finished" in c for c in chunks)


@pytest.mark.anyio
async def test_subprocess_runner_service_abort():
    runner = SubprocessRunnerService(".")
    await runner.abort()


def test_detect_runner_type():
    """Verifies that detect_runner_type accurately identifies pytest vs behave nodes."""
    from domain.models import RunnerType

    runner = SubprocessRunnerService(".")
    assert runner.detect_runner_type(None) == RunnerType.PYTEST
    assert runner.detect_runner_type(["tests/test_unit.py"]) == RunnerType.PYTEST
    assert runner.detect_runner_type(["backend/tests/acceptance"]) == RunnerType.BEHAVE
    assert runner.detect_runner_type(["features/user_login.feature"]) == RunnerType.BEHAVE


@pytest.mark.anyio
async def test_subprocess_runner_service_stream_behave(tmp_path):
    """Verifies streaming execution with Behave runner config."""
    feat_dir = tmp_path / "features"
    feat_dir.mkdir()
    feat_file = feat_dir / "sample.feature"
    feat_file.write_text("Feature: Sample\n", encoding="utf-8")

    runner = SubprocessRunnerService(str(tmp_path))
    chunks = []
    async for chunk in runner.run_test_stream(nodes=["features/sample.feature"]):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any("behave" in c for c in chunks)


@pytest.mark.anyio
async def test_subprocess_runner_service_report_json(tmp_path):
    """Verifies json report reading and error handling in summary generator."""
    import json
    from unittest.mock import patch

    runner = SubprocessRunnerService(str(tmp_path))

    # Test valid json report
    report_file = tmp_path / "report.json"

    chunks = []
    async for chunk in runner.run_test_stream(report_json_path=str(report_file)):
        chunks.append(chunk)

    finished_chunk = json.loads(chunks[-1])
    assert "report" in finished_chunk["summary"]
    assert isinstance(finished_chunk["summary"]["report"], dict)

    # Test json parsing error handling via mocked load
    report_err_file = tmp_path / "report_err.json"
    report_err_file.write_text("dummy", encoding="utf-8")

    with patch("json.load", side_effect=ValueError("Corrupt JSON")):
        chunks_err = []
        async for chunk in runner.run_test_stream(report_json_path=str(report_err_file)):
            chunks_err.append(chunk)

    finished_err_chunk = json.loads(chunks_err[-1])
    assert "report_error" in finished_err_chunk["summary"]


@pytest.mark.anyio
async def test_subprocess_runner_service_abort_running_process(tmp_path):
    """Verifies that abort() terminates active subprocesses correctly."""
    import asyncio
    from unittest.mock import MagicMock

    runner = SubprocessRunnerService(str(tmp_path))
    proc = await asyncio.create_subprocess_exec(
        "sleep", "5",
        cwd=str(tmp_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True
    )
    runner.proc = proc
    assert proc.returncode is None

    await runner.abort()
    assert proc.returncode is not None

    # Test ProcessLookupError handling when terminate fails
    mock_proc = MagicMock()
    mock_proc.returncode = None
    mock_proc.terminate.side_effect = ProcessLookupError("No such process")
    runner.proc = mock_proc
    await runner.abort()  # Should handle exception silently


@pytest.mark.anyio
async def test_subprocess_runner_service_xdist_streams_test_status_events(tmp_path):
    """Verifies that running pytest with xdist (-n 2) streams real-time test_status events without leaking markers to stdout."""
    import json

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_parallel.py"
    test_file.write_text(
        "import pytest\n"
        "def test_pass_one(): assert True\n"
        "def test_fail_two(): assert False\n"
        "@pytest.mark.skip(reason='skip')\n"
        "def test_skip_three(): pass\n",
        encoding="utf-8",
    )

    runner = SubprocessRunnerService(str(tmp_path))
    chunks = []
    async for raw_chunk in runner.run_test_stream(
        nodes=["tests/test_parallel.py"],
        extra_args=["-n", "2"],
    ):
        chunks.append(json.loads(raw_chunk))

    stdout_chunks = [c["data"] for c in chunks if c["type"] == "stdout"]
    assert not any("__PYTESTDECK_EVENT__" in s for s in stdout_chunks)

    status_events = [c for c in chunks if c["type"] == "test_status"]
    assert len(status_events) >= 3

    outcomes_by_node = {}
    for ev in status_events:
        if ev["outcome"] != "running":
            outcomes_by_node[ev["node_id"]] = ev["outcome"]

    assert outcomes_by_node.get("tests/test_parallel.py::test_pass_one") == "passed"
    assert outcomes_by_node.get("tests/test_parallel.py::test_fail_two") == "failed"
    assert outcomes_by_node.get("tests/test_parallel.py::test_skip_three") == "skipped"


@pytest.mark.anyio
async def test_subprocess_runner_service_emits_ping_heartbeat_during_silent_test(tmp_path):
    """Verifies that run_test_stream emits periodic ping heartbeats while waiting on silent tests."""
    import json

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_silent.py"
    test_file.write_text(
        "import time\n"
        "def test_silent_sleep():\n"
        "    time.sleep(0.25)\n"
        "    assert True\n",
        encoding="utf-8",
    )

    runner = SubprocessRunnerService(str(tmp_path), heartbeat_interval=0.05)
    chunks = []
    async for raw_chunk in runner.run_test_stream(nodes=["tests/test_silent.py"]):
        chunks.append(json.loads(raw_chunk))

    ping_chunks = [c for c in chunks if c.get("type") == "ping"]
    assert len(ping_chunks) >= 1
    assert any(c.get("type") == "finished" for c in chunks)


@pytest.mark.anyio
async def test_subprocess_runner_service_behave_populates_summary_counts(tmp_path):
    """Verifies that Behave runs populate summary['report']['summary'] counts from method_outputs."""
    import json

    feat_dir = tmp_path / "features"
    steps_dir = feat_dir / "steps"
    steps_dir.mkdir(parents=True)
    (feat_dir / "sample.feature").write_text(
        "Feature: Sample Metrics\n"
        "  Scenario: Passing scenario one\n"
        "    Given a passing step\n"
        "  Scenario: Failing scenario two\n"
        "    Given a failing step\n",
        encoding="utf-8",
    )
    (steps_dir / "sample_steps.py").write_text(
        "from behave import given\n"
        "@given('a passing step')\n"
        "def step_pass(context):\n"
        "    assert True\n"
        "@given('a failing step')\n"
        "def step_fail(context):\n"
        "    assert False\n",
        encoding="utf-8",
    )

    runner = SubprocessRunnerService(str(tmp_path))
    chunks = []
    async for raw_chunk in runner.run_test_stream(nodes=["features/sample.feature"]):
        chunks.append(json.loads(raw_chunk))

    finished = next(c for c in chunks if c.get("type") == "finished")
    report_summary = finished["summary"].get("report", {}).get("summary", {})
    assert report_summary.get("total") == 2
    assert report_summary.get("passed") == 1
    assert report_summary.get("failed") == 1
    assert report_summary.get("skipped") == 0


def test_pytest_status_plugin_reporter_lifecycle(monkeypatch):
    """Verifies _PytestDeckStatusReporter and pytest_configure across setup, call, teardown, and xdist worker checks."""
    import io
    import json
    from types import SimpleNamespace

    import infrastructure.pytest_status_plugin as plugin

    buf = io.StringIO()
    monkeypatch.setattr(plugin.sys, "__stdout__", buf)

    reporter = plugin._PytestDeckStatusReporter()
    # Empty node_id is ignored
    reporter._emit("", "running")
    reporter.pytest_runtest_logreport(SimpleNamespace(nodeid=""))

    # 1. Normal pass lifecycle (logstart -> setup -> call -> teardown)
    reporter.pytest_runtest_logstart("tests/test_a.py::test_ok", ("tests/test_a.py", 1, "test_ok"))
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_ok", when="setup", duration=0.01, failed=False, skipped=False)
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_ok", when="call", duration=0.02, failed=False, skipped=False)
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_ok", when="teardown", duration=0.01, failed=False, skipped=False)
    )

    # 2. Setup skip and setup failure
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_setup_skip", when="setup", duration=0.001, failed=False, skipped=True)
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_setup_fail", when="setup", duration=0.002, failed=True, skipped=False)
    )

    # 3. Call xfail, call skip, call fail, and teardown failure overriding pass
    reporter.pytest_runtest_logreport(
        SimpleNamespace(
            nodeid="tests/test_a.py::test_xfail", when="call", duration=0.01, failed=True, skipped=False, wasxfail="reason"
        )
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_call_skip", when="call", duration=0.01, failed=False, skipped=True)
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_teardown_err", when="call", duration=0.01, failed=False, skipped=False)
    )
    reporter.pytest_runtest_logreport(
        SimpleNamespace(nodeid="tests/test_a.py::test_teardown_err", when="teardown", duration=0.01, failed=True, skipped=False)
    )

    raw_lines = buf.getvalue().splitlines()
    assert all(line.startswith(plugin.EVENT_PREFIX) for line in raw_lines)
    lines = [
        json.loads(line.split(plugin.EVENT_PREFIX, 1)[1])
        for line in raw_lines
        if line.startswith(plugin.EVENT_PREFIX)
    ]
    by_node = {}
    for item in lines:
        by_node.setdefault(item["node_id"], []).append(item)

    assert by_node["tests/test_a.py::test_ok"][0]["outcome"] == "running"
    assert by_node["tests/test_a.py::test_ok"][-1] == {
        "node_id": "tests/test_a.py::test_ok",
        "outcome": "passed",
        "duration": 0.04,
    }
    assert by_node["tests/test_a.py::test_setup_skip"][-1]["outcome"] == "skipped"
    assert by_node["tests/test_a.py::test_setup_fail"][-1]["outcome"] == "failed"
    assert by_node["tests/test_a.py::test_xfail"][-1]["outcome"] == "skipped"
    assert by_node["tests/test_a.py::test_call_skip"][-1]["outcome"] == "skipped"
    assert by_node["tests/test_a.py::test_teardown_err"][-1]["outcome"] == "failed"

    # Verify pytest_configure skips registration on xdist workers and registers on controller
    registered = []
    worker_cfg = SimpleNamespace(
        workerinput={},
        pluginmanager=SimpleNamespace(
            has_plugin=lambda _: False,
            register=lambda p, name: registered.append(name),
        ),
    )
    plugin.pytest_configure(worker_cfg)
    assert registered == []

    controller_cfg = SimpleNamespace(
        pluginmanager=SimpleNamespace(
            has_plugin=lambda _: False,
            register=lambda p, name: registered.append(name),
        ),
    )
    plugin.pytest_configure(controller_cfg)
    assert registered == ["pytestdeck_status_reporter"]


@pytest.mark.anyio
async def test_subprocess_runner_service_handles_oversized_stdout_line(tmp_path):
    """Verifies that lines exceeding 64KB default asyncio StreamReader limit do not raise LimitOverrunError."""
    import json

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    test_file = test_dir / "test_big_line.py"
    test_file.write_text(
        "def test_emit_huge_line():\n"
        "    print('X' * 100_000, flush=True)\n"
        "    assert True\n",
        encoding="utf-8",
    )

    runner = SubprocessRunnerService(str(tmp_path))
    chunks = []
    async for raw_chunk in runner.run_test_stream(nodes=["tests/test_big_line.py"], extra_args=["-s"]):
        chunks.append(json.loads(raw_chunk))

    stdout_text = "".join(c["data"] for c in chunks if c.get("type") == "stdout")
    assert "X" * 100_000 in stdout_text
    finished = next(c for c in chunks if c.get("type") == "finished")
    assert finished["exit_code"] == 0


@pytest.mark.anyio
async def test_read_stream_line_recovers_from_limit_overrun():
    """Verifies _read_stream_line drains oversized chunk when LimitOverrunError/ValueError occurs."""
    import asyncio

    from infrastructure.runner_service import _read_stream_line

    reader = asyncio.StreamReader(limit=32)
    reader.feed_data(b"A" * 100 + b"\n")
    reader.feed_eof()

    chunk = await _read_stream_line(reader)
    assert chunk.startswith(b"A" * 32)


@pytest.mark.anyio
async def test_subprocess_runner_service_logs_warning_on_history_persistence_error(tmp_path, monkeypatch, caplog):
    """Verifies that history database persistence errors are logged as warnings rather than swallowed silently."""
    import json
    import logging

    from infrastructure.history_db import HistoryDatabase

    test_dir = tmp_path / "tests"
    test_dir.mkdir()
    (test_dir / "test_log_warn.py").write_text("def test_pass(): assert True\n", encoding="utf-8")

    def boom_save_runs(self, *args, **kwargs):
        raise RuntimeError("disk I/O error")

    monkeypatch.setattr(HistoryDatabase, "save_runs", boom_save_runs)

    runner = SubprocessRunnerService(str(tmp_path))
    with caplog.at_level(logging.WARNING, logger="infrastructure.runner_service"):
        chunks = []
        async for raw_chunk in runner.run_test_stream(nodes=["tests/test_log_warn.py"]):
            chunks.append(json.loads(raw_chunk))

    assert any(c.get("type") == "finished" for c in chunks)
    assert any("Failed to persist test run history" in rec.message for rec in caplog.records)







