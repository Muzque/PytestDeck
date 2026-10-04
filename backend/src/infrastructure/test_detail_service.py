import ast
import hashlib
import inspect
import re
from pathlib import Path
from typing import Any

from domain.services import is_safe_subpath, resolve_target_path


def parse_gherkin_scenarios(feature_path: Path) -> list[dict[str, Any]]:
    """Parses scenarios, steps, tags, and docstrings from a Gherkin .feature file.

    Args:
        feature_path: Path to the .feature file.

    Returns:
        list[dict[str, Any]]: List of parsed scenarios with metadata.
    """
    if not feature_path.exists():
        return []

    try:
        content = feature_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    lines = content.splitlines()
    scenarios: list[dict[str, Any]] = []
    current_scenario: dict[str, Any] | None = None
    feature_title = ""
    feature_description: list[str] = []
    in_feature_header = False
    pending_tags: list[str] = []
    in_docstring_block = False
    docstring_lines: list[str] = []

    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("@"):
            tags = [t.strip() for t in line.split() if t.strip().startswith("@")]
            pending_tags.extend(tags)
            continue

        if line.startswith("Feature:"):
            feature_title = line.split(":", 1)[1].strip()
            in_feature_header = True
            continue

        if line.startswith(('Scenario:', 'Scenario Outline:')):
            in_feature_header = False
            title = line.split(":", 1)[1].strip()
            current_scenario = {
                "title": title,
                "line": idx,
                "tags": list(pending_tags),
                "steps": [],
                "description_lines": [],
                "feature_title": feature_title,
            }
            pending_tags.clear()
            scenarios.append(current_scenario)
            continue

        if in_feature_header and not current_scenario:
            if not any(line.startswith(k) for k in ('Scenario:', 'Scenario Outline:', '@')):
                feature_description.append(line)
            continue

        if current_scenario:
            if line.startswith(('"""', "'''")):
                in_docstring_block = not in_docstring_block
                continue

            if in_docstring_block:
                docstring_lines.append(raw_line)
                continue

            if any(line.startswith(k) for k in ('Given ', 'When ', 'Then ', 'And ', 'But ')):
                current_scenario["steps"].append(line)
            else:
                current_scenario["description_lines"].append(line)

    return scenarios


def get_feature_detail(feature_path: Path, scenario_name: str | None = None) -> dict[str, Any]:
    """Extracts scenario or feature details and docstring from a .feature file.

    Args:
        feature_path: Path to the .feature file.
        scenario_name: Optional scenario title.

    Returns:
        dict[str, Any]: Test detail dictionary.
    """
    scenarios = parse_gherkin_scenarios(feature_path)
    feature_title = ""
    feature_desc_lines: list[str] = []
    file_mtime = feature_path.stat().st_mtime if feature_path.exists() else None

    try:
        content = feature_path.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("Feature:"):
                feature_title = s.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    if scenario_name:
        for sc in scenarios:
            if sc["title"].strip() == scenario_name.strip():
                desc = "\n".join(sc["description_lines"]).strip() if sc["description_lines"] else None
                raw_scenario = "\n".join([sc["title"]] + sc["steps"] + sc["description_lines"])
                code_hash = hashlib.sha256(raw_scenario.strip().encode("utf-8")).hexdigest()[:16]
                return {
                    "name": sc["title"],
                    "type": "scenario",
                    "file_path": str(feature_path),
                    "line_number": sc["line"],
                    "docstring": desc,
                    "class_name": None,
                    "parameters": None,
                    "decorators": sc["tags"],
                    "steps": sc["steps"],
                    "feature_title": sc.get("feature_title") or feature_title,
                    "tags": sc["tags"],
                    "code_hash": code_hash,
                    "file_mtime": file_mtime,
                }

    # Fallback to feature file detail
    raw_feature = "\n".join([feature_title] + feature_desc_lines + [s["title"] for s in scenarios])
    code_hash = hashlib.sha256(raw_feature.strip().encode("utf-8")).hexdigest()[:16]
    return {
        "name": feature_title or feature_path.name,
        "type": "feature",
        "file_path": str(feature_path),
        "line_number": 1,
        "docstring": "\n".join(feature_desc_lines).strip() if feature_desc_lines else None,
        "class_name": None,
        "parameters": None,
        "decorators": [],
        "steps": [s["title"] for s in scenarios],
        "feature_title": feature_title,
        "tags": [],
        "code_hash": code_hash,
        "file_mtime": file_mtime,
    }


def _format_decorator(dec_node: ast.AST) -> str:
    """Formats an AST decorator node into a readable string representation."""
    try:
        return f"@{ast.unparse(dec_node)}"
    except Exception:
        if isinstance(dec_node, ast.Name):
            return f"@{dec_node.id}"
        if isinstance(dec_node, ast.Attribute):
            return f"@{ast.unparse(dec_node)}"
        return "@decorator"


def get_python_test_detail(file_path: Path, parts: list[str]) -> dict[str, Any]:
    """Extracts test function, method, or class metadata and docstrings using AST.

    Args:
        file_path: Path to the target Python test file.
        parts: List of path components split by '::' (e.g. ['test_foo'] or ['TestBar', 'test_method']).

    Returns:
        dict[str, Any]: Test detail dictionary.
    """
    content = file_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(content, filename=str(file_path))
    file_mtime = file_path.stat().st_mtime if file_path.exists() else None

    if not parts:
        # File module level docstring
        module_doc = ast.get_docstring(tree)
        code_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()[:16]
        return {
            "name": file_path.name,
            "type": "file",
            "file_path": str(file_path),
            "line_number": 1,
            "docstring": inspect.cleandoc(module_doc) if module_doc else None,
            "class_name": None,
            "parameters": None,
            "decorators": [],
            "steps": None,
            "feature_title": None,
            "tags": None,
            "code_hash": code_hash,
            "file_mtime": file_mtime,
        }

    # Clean parameterization like test_func[param1-param2]
    clean_parts = [re.sub(r"\[.*\]$", "", p) for p in parts]

    target_class_name = clean_parts[0] if len(clean_parts) > 1 else None
    target_func_name = clean_parts[-1]

    # Search for class first if specified
    current_scope = tree.body
    class_docstring = None
    if target_class_name:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                class_docstring = ast.get_docstring(node)
                current_scope = node.body
                break

    # Search for target function / method
    for node in current_scope:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target_func_name:
            doc = ast.get_docstring(node)
            params = [a.arg for a in node.args.args if a.arg != "self"]
            decorators = [_format_decorator(d) for d in node.decorator_list]
            source_seg = ast.get_source_segment(content, node)
            code_hash = hashlib.sha256(source_seg.strip().encode("utf-8")).hexdigest()[:16] if source_seg else None
            return {
                "name": node.name,
                "type": "function",
                "file_path": str(file_path),
                "line_number": node.lineno,
                "docstring": inspect.cleandoc(doc) if doc else None,
                "class_name": target_class_name,
                "class_docstring": inspect.cleandoc(class_docstring) if class_docstring else None,
                "parameters": params,
                "decorators": decorators,
                "steps": None,
                "feature_title": None,
                "tags": None,
                "code_hash": code_hash,
                "file_mtime": file_mtime,
            }

    # If class itself was targeted
    if target_class_name and not len(clean_parts) > 1:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                doc = ast.get_docstring(node)
                source_seg = ast.get_source_segment(content, node)
                code_hash = hashlib.sha256(source_seg.strip().encode("utf-8")).hexdigest()[:16] if source_seg else None
                return {
                    "name": node.name,
                    "type": "class",
                    "file_path": str(file_path),
                    "line_number": node.lineno,
                    "docstring": inspect.cleandoc(doc) if doc else None,
                    "class_name": target_class_name,
                    "parameters": None,
                    "decorators": [_format_decorator(d) for d in node.decorator_list],
                    "steps": None,
                    "feature_title": None,
                    "tags": None,
                    "code_hash": code_hash,
                    "file_mtime": file_mtime,
                }

    return {
        "name": target_func_name,
        "type": "function",
        "file_path": str(file_path),
        "line_number": None,
        "docstring": None,
        "class_name": target_class_name,
        "parameters": None,
        "decorators": [],
        "steps": None,
        "feature_title": None,
        "tags": None,
        "code_hash": None,
        "file_mtime": file_mtime,
    }


def get_node_code_metadata(target_dir: Path, node_id: str) -> tuple[str | None, float | None]:
    """Helper to quickly obtain (code_hash, file_mtime) for a given node ID."""
    try:
        parts = node_id.split("::")
        rel_file = parts[0]
        sub_parts = parts[1:] if len(parts) > 1 else []
        full_path = (target_dir / rel_file).resolve()
        if not full_path.exists():
            return None, None

        if rel_file.endswith(".feature"):
            scenario_name = sub_parts[0] if sub_parts else None
            detail = get_feature_detail(full_path, scenario_name=scenario_name)
        else:
            detail = get_python_test_detail(full_path, sub_parts)
        return detail.get("code_hash"), detail.get("file_mtime")
    except Exception:
        return None, None


def extract_test_detail(target_path: str, node_id: str) -> dict[str, Any]:
    """Coordinates test method docstring and metadata extraction for Pytest and Behave.

    Args:
        target_path: Absolute or default path of the repository root.
        node_id: Test node identifier (e.g. 'tests/unit/test_a.py::test_func').

    Returns:
        dict[str, Any]: Complete test method detail dictionary including latest run and code modification check.

    Raises:
        ValueError: If node path is unsafe or file does not exist.
    """
    target_dir = resolve_target_path(target_path)

    if not is_safe_subpath(target_dir, node_id):
        raise ValueError(f"Unsafe node path detected: {node_id}")

    parts = node_id.split("::")
    rel_file = parts[0]
    sub_parts = parts[1:] if len(parts) > 1 else []

    full_path = (target_dir / rel_file).resolve()
    if not full_path.exists():
        raise ValueError(f"Test file not found: {rel_file}")

    if rel_file.endswith(".feature"):
        scenario_name = sub_parts[0] if sub_parts else None
        res = get_feature_detail(full_path, scenario_name=scenario_name)
    else:
        res = get_python_test_detail(full_path, sub_parts)

    res["node_id"] = node_id
    res["file_path"] = rel_file

    # Check HistoryDatabase for stored run and code modification comparison
    try:
        from infrastructure.history_db import HistoryDatabase
        db = HistoryDatabase(target_path=target_dir)
        stored_run = db.get_run(node_id)
        if stored_run:
            res["latest_run"] = stored_run
            curr_hash = res.get("code_hash")
            stored_hash = stored_run.get("code_hash")
            curr_mtime = res.get("file_mtime")
            stored_mtime = stored_run.get("file_mtime")

            if curr_hash and stored_hash:
                res["modified_since_run"] = bool(curr_hash != stored_hash)
            elif curr_mtime and stored_mtime:
                res["modified_since_run"] = bool(curr_mtime > stored_mtime + 1.0)
            else:
                res["modified_since_run"] = False
        else:
            res["latest_run"] = None
            res["modified_since_run"] = False
    except Exception:
        res["latest_run"] = None
        res["modified_since_run"] = False

    return res
