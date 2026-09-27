from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    """Enumeration of supported test tree node types."""

    DIRECTORY = "directory"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"


@dataclass
class TestNode:
    """Represents a single node within the hierarchical test explorer tree.

    Attributes:
        id: Unique identifier for the test node (e.g. file path or pytest nodeid).
        name: Display name of the node (file name, class name, or test function name).
        type: The category of node represented by NodeType enum.
        path: Relative file path associated with the test node.
        children: Child test nodes contained under this directory, file, or class.
    """

    id: str
    name: str
    type: NodeType
    path: str
    children: list["TestNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converts the TestNode dataclass instance into a dictionary structure.

        Returns:
            dict[str, Any]: Serialized dictionary representation of the node.
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "path": self.path,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class TestTree:
    """Represents a complete collected test tree response for a target repository.

    Attributes:
        target_path: Absolute directory path of the target Python project repository.
        suite: Relative path of the target test suite directory.
        total_nodes: Total count of executable test items collected.
        root: Root TestNode directory structure containing collected test nodes.
    """

    target_path: str
    suite: str
    total_nodes: int
    root: TestNode

    def to_dict(self) -> dict[str, Any]:
        """Converts the TestTree dataclass instance into a dictionary structure.

        Returns:
            dict[str, Any]: Serialized dictionary representation of the tree.
        """
        return {
            "target_path": self.target_path,
            "suite": self.suite,
            "total_nodes": self.total_nodes,
            "tree": self.root.to_dict(),
        }
