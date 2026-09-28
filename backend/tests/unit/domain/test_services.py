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

