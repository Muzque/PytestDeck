from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NodeType(str, Enum):
    DIRECTORY = "directory"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"


@dataclass
class TestNode:
    id: str
    name: str
    type: NodeType
    path: str
    children: list["TestNode"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "path": self.path,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class TestTree:
    target_path: str
    suite: str
    total_nodes: int
    root: TestNode

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_path": self.target_path,
            "suite": self.suite,
            "total_nodes": self.total_nodes,
            "tree": self.root.to_dict(),
        }
