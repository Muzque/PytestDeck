import pytest

from application.use_cases import DiscoverTestsUseCase


@pytest.mark.anyio
async def test_discover_tests_use_case_valid(tmp_path):
    test_dir = tmp_path / "tests" / "unit"
    test_dir.mkdir(parents=True)
    test_file = test_dir / "test_sample.py"
    test_file.write_text("def test_ok(): pass\n", encoding="utf-8")

    use_case = DiscoverTestsUseCase()
    res = await use_case.execute(str(tmp_path), suite_rel_path="tests/unit")
    assert res.target_path == str(tmp_path.resolve())
    assert res.suite == "tests/unit"


@pytest.mark.anyio
async def test_discover_tests_use_case_invalid_path():
    use_case = DiscoverTestsUseCase()
    with pytest.raises(ValueError, match="Invalid target path"):
        await use_case.execute("/path/that/does/not/exist/xyz123")
