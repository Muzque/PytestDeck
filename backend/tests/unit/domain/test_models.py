from domain.models import NodeType, TestNode, TestTree


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
