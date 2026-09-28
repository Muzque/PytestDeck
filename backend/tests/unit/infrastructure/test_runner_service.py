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
        stderr=asyncio.subprocess.PIPE
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

