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
    async for chunk in runner.run_pytest_stream(nodes=["tests/test_dummy.py"]):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any("Started process" in c for c in chunks)
    assert any("finished" in c for c in chunks)


@pytest.mark.anyio
async def test_subprocess_runner_service_abort():
    runner = SubprocessRunnerService(".")
    await runner.abort()
