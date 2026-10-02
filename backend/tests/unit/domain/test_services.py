from domain.models import NodeType
from domain.services import build_tree_from_collectors


def test_build_tree_from_collectors_empty():
    tree = build_tree_from_collectors([])
    assert tree.id == "root"
    assert tree.children == []


def test_build_tree_from_collectors_sample():
    collectors = [
        {
            "result": [
                {"nodeid": "tests/unit/test_demo.py::test_func", "type": "Function"}
            ]
        }
    ]
    tree = build_tree_from_collectors(collectors, suite_prefix="tests/unit")
    assert tree.id == "tests/unit"
    assert len(tree.children) > 0
    assert tree.children[0].name == "test_demo.py"
    assert tree.children[0].type == NodeType.FILE


def test_build_tree_from_collectors_relative_nodeid():
    """Verifies prefixing when nodeid does not start with suite_prefix."""
    collectors = [
        {
            "result": [
                {"nodeid": "test_demo.py::test_func", "type": "Function"}
            ]
        }
    ]
    tree = build_tree_from_collectors(collectors, suite_prefix="tests/unit")
    assert tree.id == "tests/unit"
    assert len(tree.children) > 0
    assert tree.children[0].name == "test_demo.py"


def test_is_safe_subpath(tmp_path):
    from domain.services import is_safe_subpath
    assert is_safe_subpath(tmp_path, "") is True
    assert is_safe_subpath(tmp_path, "tests/unit/test_a.py::test_fn") is True
    assert is_safe_subpath(tmp_path, "../../etc/passwd") is False


def test_resolve_target_path(tmp_path):
    import pytest

    from domain.services import resolve_target_path

    # Valid existing path
    res = resolve_target_path(str(tmp_path))
    assert res == tmp_path.resolve()

    # Empty target_path fallback
    default_res = resolve_target_path("")
    assert default_res.exists()

    # Invalid nonexistent target_path
    with pytest.raises(ValueError, match="Invalid target path"):
        resolve_target_path(str(tmp_path / "nonexistent_dir_12345"))


