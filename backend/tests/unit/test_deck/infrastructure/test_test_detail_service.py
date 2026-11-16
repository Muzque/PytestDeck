from pathlib import Path

import pytest

from infrastructure.test_detail_service import (
    extract_test_detail,
    get_feature_detail,
    get_python_test_detail,
    parse_gherkin_scenarios,
)


def test_get_python_test_detail_standalone_function(tmp_path: Path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        'def test_simple_case():\n'
        '    """Verifies simple arithmetic calculation."""\n'
        '    assert 1 + 1 == 2\n',
        encoding="utf-8",
    )

    detail = get_python_test_detail(test_file, ["test_simple_case"])
    assert detail["name"] == "test_simple_case"
    assert detail["type"] == "function"
    assert detail["line_number"] == 1
    assert detail["docstring"] == "Verifies simple arithmetic calculation."
    assert detail["class_name"] is None
    assert detail["parameters"] == []


def test_get_python_test_detail_class_method(tmp_path: Path):
    test_file = tmp_path / "test_cls.py"
    test_file.write_text(
        'class TestSuite:\n'
        '    """Test suite docstring."""\n'
        '    @pytest.mark.asyncio\n'
        '    async def test_async_method(self, client, auth_token):\n'
        '        """Async method docstring description."""\n'
        '        pass\n',
        encoding="utf-8",
    )

    detail = get_python_test_detail(test_file, ["TestSuite", "test_async_method"])
    assert detail["name"] == "test_async_method"
    assert detail["type"] == "function"
    assert detail["class_name"] == "TestSuite"
    assert detail["class_docstring"] == "Test suite docstring."
    assert detail["docstring"] == "Async method docstring description."
    assert detail["parameters"] == ["client", "auth_token"]
    assert any("@pytest.mark.asyncio" in d for d in detail["decorators"])


def test_get_python_test_detail_parameterized_and_no_docstring(tmp_path: Path):
    test_file = tmp_path / "test_param.py"
    test_file.write_text(
        'def test_with_params(a, b):\n'
        '    assert a == b\n',
        encoding="utf-8",
    )

    # Node ID with parameter notation
    detail = get_python_test_detail(test_file, ["test_with_params[1-1]"])
    assert detail["name"] == "test_with_params"
    assert detail["docstring"] is None
    assert detail["parameters"] == ["a", "b"]


def test_parse_gherkin_scenarios_and_detail(tmp_path: Path):
    feat_file = tmp_path / "feature_sample.feature"
    feat_file.write_text(
        '@smoke\n'
        'Feature: User Authentication\n'
        '  As a registered user, I want to authenticate.\n'
        '\n'
        '  @critical\n'
        '  Scenario: Successful login with valid credentials\n'
        '    Docstring line for login scenario.\n'
        '    Given valid user credentials "alice"\n'
        '    When login request is submitted\n'
        '    Then session token is returned\n',
        encoding="utf-8",
    )

    scenarios = parse_gherkin_scenarios(feat_file)
    assert len(scenarios) == 1
    assert scenarios[0]["title"] == "Successful login with valid credentials"
    assert "@critical" in scenarios[0]["tags"]
    assert len(scenarios[0]["steps"]) == 3

    detail = get_feature_detail(feat_file, scenario_name="Successful login with valid credentials")
    assert detail["name"] == "Successful login with valid credentials"
    assert detail["type"] == "scenario"
    assert detail["docstring"] == "Docstring line for login scenario."
    assert detail["feature_title"] == "User Authentication"
    assert len(detail["steps"]) == 3


def test_extract_test_detail_safe_and_error_handling(tmp_path: Path):
    test_file = tmp_path / "test_xyz.py"
    test_file.write_text("def test_one():\n    '''Hello world doc.'''\n    pass\n", encoding="utf-8")

    # Success case
    detail = extract_test_detail(str(tmp_path), "test_xyz.py::test_one")
    assert detail["name"] == "test_one"
    assert detail["docstring"] == "Hello world doc."

    # Unsafe path traversal
    with pytest.raises(ValueError, match="Unsafe node path"):
        extract_test_detail(str(tmp_path), "../../etc/passwd::root")

    # Missing file
    with pytest.raises(ValueError, match="Test file not found"):
        extract_test_detail(str(tmp_path), "nonexistent.py::test_foo")


def test_get_node_code_metadata_caches_ast_parsing_per_file(tmp_path: Path, monkeypatch):
    """Verifies that get_node_code_metadata parses each Python file only once when a shared cache is provided."""
    import ast

    from infrastructure.test_detail_service import get_node_code_metadata

    test_file = tmp_path / "test_many.py"
    test_file.write_text(
        "def test_alpha():\n    assert 1 == 1\n\n"
        "def test_beta():\n    assert 2 == 2\n\n"
        "def test_gamma():\n    assert 3 == 3\n",
        encoding="utf-8",
    )

    parse_calls = 0
    real_parse = ast.parse

    def counting_parse(*args, **kwargs):
        nonlocal parse_calls
        parse_calls += 1
        return real_parse(*args, **kwargs)

    monkeypatch.setattr(ast, "parse", counting_parse)

    cache = {}
    h1, m1 = get_node_code_metadata(tmp_path, "test_many.py::test_alpha", cache=cache)
    h2, m2 = get_node_code_metadata(tmp_path, "test_many.py::test_beta", cache=cache)
    h3, m3 = get_node_code_metadata(tmp_path, "test_many.py::test_gamma", cache=cache)

    assert h1 and h2 and h3
    assert h1 != h2 != h3
    assert m1 == m2 == m3
    assert parse_calls == 1

