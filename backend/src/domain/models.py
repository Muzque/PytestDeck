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

    __test__ = False

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

    __test__ = False

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

class RunnerType(str, Enum):
    """Enumeration of supported test runner frameworks."""

    PYTEST = "pytest"
    BEHAVE = "behave"


@dataclass
class BaseExecutionConfig:
    """Base dataclass for framework-specific execution configurations.

    Attributes:
        nodes: Target node paths or nodeids to execute.
        extra_args: Additional command line flags.
    """

    nodes: list[str] = field(default_factory=list)
    extra_args: list[str] = field(default_factory=list)

    def build_command(self) -> list[str]:
        """Constructs the CLI command array. Overridden by subclasses.

        Raises:
            NotImplementedError: Must be implemented by concrete runner configs.
        """
        raise NotImplementedError


@dataclass
class PytestConfig(BaseExecutionConfig):
    """Execution configuration tailored specifically for Pytest test runs.

    Attributes:
        marker: Optional pytest marker filter expression (e.g. -m smoke).
        report_json_path: Optional output path for pytest-json-report plugin.
    """

    marker: str | None = None
    report_json_path: str | None = None

    def build_command(self) -> list[str]:
        """Constructs the complete Pytest CLI command.

        Returns:
            list[str]: CLI command arguments array for pytest.
        """
        cmd = ["uv", "run"]
        if self.report_json_path:
            # Inject the plugin so target repos don't need it in their lockfile
            cmd.extend(["--with", "pytest-json-report"])
        cmd.extend(["pytest", "-v", "--color=yes"])
        if self.report_json_path:
            cmd.extend(["--json-report", f"--json-report-file={self.report_json_path}"])
        if self.marker:
            cmd.extend(["-m", self.marker])
        if self.extra_args:
            cmd.extend(self.extra_args)
        if self.nodes:
            cmd.extend(self.nodes)
        return cmd


@dataclass
class BehaveConfig(BaseExecutionConfig):
    """Execution configuration tailored specifically for Behave BDD test runs."""

    def build_command(self) -> list[str]:
        """Constructs the complete Behave CLI command.

        Returns:
            list[str]: CLI command arguments array for behave.
        """
        import re

        cmd = ["uv", "run", "behave", "--color=always"]
        if self.extra_args:
            cmd.extend(self.extra_args)
        if self.nodes:
            has_scenario = any("::" in n for n in self.nodes)
            if not has_scenario:
                cmd.extend(self.nodes)
            else:
                files_to_run = []
                scenario_names = []
                for n in self.nodes:
                    if "::" in n:
                        file_part, sname = n.split("::", 1)
                        if file_part not in files_to_run:
                            files_to_run.append(file_part)
                        scenario_names.append(sname)
                    else:
                        if n not in files_to_run:
                            files_to_run.append(n)
                if scenario_names:
                    regex = "^(" + "|".join(re.escape(s) for s in scenario_names) + ")$"
                    cmd.extend(["-n", regex])
                cmd.extend(files_to_run)
        return cmd



