import pytest

from domain.models import (
    BaseExecutionConfig,
    BehaveConfig,
    NodeType,
    PytestConfig,
    TestNode,
    TestTree,
)


def test_test_node_to_dict():
    node = TestNode(
        id="tests/unit/test_demo.py::test_func",
        name="test_func",
        type=NodeType.FUNCTION,
        path="tests/unit/test_demo.py",
        children=[],
    )
    data = node.to_dict()
    assert data["id"] == "tests/unit/test_demo.py::test_func"
    assert data["type"] == "function"
    assert data["children"] == []


def test_test_tree_to_dict():
    root_node = TestNode(
        id="root",
        name="tests",
        type=NodeType.DIRECTORY,
        path="tests",
        children=[],
    )
    tree = TestTree(
        target_path="/tmp/test",
        suite="tests/unit",
        total_nodes=1,
        root=root_node,
    )
    data = tree.to_dict()
    assert data["target_path"] == "/tmp/test"
    assert data["suite"] == "tests/unit"
    assert data["total_nodes"] == 1
    assert data["tree"]["id"] == "root"


def test_base_execution_config_raises_not_implemented():
    """Verifies that BaseExecutionConfig.build_command raises NotImplementedError."""
    config = BaseExecutionConfig()
    with pytest.raises(NotImplementedError):
        config.build_command()


def test_pytest_config_build_command():
    """Verifies that PytestConfig constructs correct command line arguments."""
    # Default command
    cfg = PytestConfig()
    assert cfg.build_command() == ["uv", "run", "pytest", "-v", "--color=yes"]

    # Full command with options
    cfg_full = PytestConfig(
        marker="smoke",
        report_json_path="/tmp/report.json",
        extra_args=["-s"],
        nodes=["tests/test_a.py"],
    )
    cmd = cfg_full.build_command()
    assert cmd == [
        "uv",
        "run",
        "--with",
        "pytest-json-report",
        "pytest",
        "-v",
        "--color=yes",
        "--json-report",
        "--json-report-file=/tmp/report.json",
        "-m",
        "smoke",
        "-s",
        "tests/test_a.py",
    ]


def test_behave_config_build_command():
    """Verifies that BehaveConfig constructs correct command line arguments."""
    # Default command
    cfg = BehaveConfig()
    assert cfg.build_command() == ["uv", "run", "behave", "--color=always"]

    # Command with nodes and extra_args
    cfg_full = BehaveConfig(
        extra_args=["--tags=@smoke"],
        nodes=["tests/acceptance", "features/login.feature"],
    )
    cmd = cfg_full.build_command()
    assert cmd == [
        "uv",
        "run",
        "behave",
        "--color=always",
        "--tags=@smoke",
        "tests/acceptance",
        "features/login.feature",
    ]


def test_behave_config_translates_s_flag():
    """Verifies that -s flag is translated to --no-capture for Behave."""
    cfg = BehaveConfig(extra_args=["-s", "--tags=@portal"], nodes=["features/login.feature"])
    cmd = cfg.build_command()
    assert "--no-capture" in cmd
    assert "-s" not in cmd


