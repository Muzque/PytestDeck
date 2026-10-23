import datetime
import re
from typing import Any

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PYTEST_NODE_PREFIX_PATTERN = re.compile(r"^([a-zA-Z0-9_\-\./\\]+\.py::[a-zA-Z0-9_\-\.:]+)(.*)$")
BEHAVE_SCENARIO_PATTERN = re.compile(r"^(?:Scenario|Scenario Outline):\s*(.*?)(?:\s+#\s*([^\s:]+\.feature)(?::\d+)?)?$")
BEHAVE_FEATURE_PATTERN = re.compile(r"^Feature:\s*(.*?)(?:\s+#\s*([^\s:]+\.feature)(?::\d+)?)?$")
BEHAVE_STEP_DURATION_PATTERN = re.compile(r"#\s+\S+:\d+\s+(\d+(?:\.\d+)?)s\s*$")


def _extract_pytest_node_id(line: str) -> str | None:
    """Extracts a full pytest node ID from a line, including parametrized [...] with arbitrary characters."""
    stripped = line.strip()
    m = PYTEST_NODE_PREFIX_PATTERN.match(stripped)
    if not m:
        return None
    prefix, rest = m.group(1), m.group(2)
    if not rest.startswith("["):
        return prefix
    depth = 0
    for idx, ch in enumerate(rest):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return prefix + rest[: idx + 1]
    return prefix + rest.split()[0]


def _is_same_test_node_at_path_boundary(node_a: str, node_b: str) -> bool:
    """Checks if two node IDs refer to the same test item with identical :: tail and / path boundary."""
    norm_a = node_a.replace("\\", "/")
    norm_b = node_b.replace("\\", "/")
    if norm_a == norm_b:
        return True
    if "::" not in norm_a or "::" not in norm_b:
        return norm_a.endswith("/" + norm_b) or norm_b.endswith("/" + norm_a)
    file_a, tail_a = norm_a.split("::", 1)
    file_b, tail_b = norm_b.split("::", 1)
    if tail_a != tail_b:
        return False
    return file_a == file_b or file_a.endswith("/" + file_b) or file_b.endswith("/" + file_a)


class MethodOutputCollector:
    """Collects, segments, and attributes console output lines to individual test methods and scenarios."""

    def __init__(self, requested_nodes: list[str] | None = None):
        self.requested_nodes = requested_nodes or []
        is_single_leaf = False
        if len(self.requested_nodes) == 1:
            req = self.requested_nodes[0]
            if "::" in req:
                parts = req.split("::")
                leaf = parts[-1]
                # A class node has 2 parts where the second part starts with capital and not test_
                if not (len(parts) == 2 and leaf[0].isupper() and not leaf.startswith("test_")):
                    is_single_leaf = True
        self.is_single_node = is_single_leaf
        self.single_node_id = self.requested_nodes[0] if self.is_single_node else None

        self.method_outputs: dict[str, dict[str, Any]] = {}
        self.current_node: str | None = None
        self.current_feature_file: str | None = None
        self.in_failures_section: bool = False
        self.current_failure_node: str | None = None

        if self.single_node_id:
            self._ensure_node(self.single_node_id)
            self.current_node = self.single_node_id

    def _ensure_node(self, node_id: str) -> None:
        if node_id not in self.method_outputs:
            self.method_outputs[node_id] = {
                "node_id": node_id,
                "lines": [],
                "outcome": "unknown",
                "duration": None,
                "timestamp": datetime.datetime.now(datetime.UTC).strftime("%H:%M:%S UTC"),
            }

    def _accumulate_behave_step_duration(self, node_id: str, clean_line: str) -> None:
        if ".feature::" not in node_id or node_id not in self.method_outputs:
            return
        step_match = BEHAVE_STEP_DURATION_PATTERN.search(clean_line)
        if step_match:
            step_dur = float(step_match.group(1))
            prev = self.method_outputs[node_id]["duration"]
            self.method_outputs[node_id]["duration"] = round((prev or 0.0) + step_dur, 4)

    def _finalize_behave_scenario(self) -> None:
        if (
            self.current_node
            and ".feature::" in self.current_node
            and self.current_node in self.method_outputs
            and self.method_outputs[self.current_node]["outcome"] == "unknown"
        ):
            self.method_outputs[self.current_node]["outcome"] = "passed"

    def process_line(self, raw_line: str) -> None:
        """Processes a single streamed stdout line, segmenting output by test method boundaries."""
        clean = ANSI_ESCAPE.sub("", raw_line).rstrip("\r\n")
        stripped = clean.strip()

        # If a single targeted method is executed, attribute all process lines to it
        if self.is_single_node and self.single_node_id:
            self.method_outputs[self.single_node_id]["lines"].append(raw_line)
            self._accumulate_behave_step_duration(self.single_node_id, clean)
            if "PASSED" in clean and self.method_outputs[self.single_node_id]["outcome"] == "unknown":
                self.method_outputs[self.single_node_id]["outcome"] = "passed"
            elif "FAILED" in clean or "\x1b[31m" in raw_line or "Assertion Failed:" in clean or "Traceback (most recent call last):" in clean:
                self.method_outputs[self.single_node_id]["outcome"] = "failed"
            elif "SKIPPED" in clean and self.method_outputs[self.single_node_id]["outcome"] == "unknown":
                self.method_outputs[self.single_node_id]["outcome"] = "skipped"
            elif (
                ".feature::" in self.single_node_id
                and re.match(r"^\d+\s+features?\s+passed", stripped)
                and self.method_outputs[self.single_node_id]["outcome"] == "unknown"
            ):
                self.method_outputs[self.single_node_id]["outcome"] = "passed"
            return

        # Check for Behave feature header
        feat_match = BEHAVE_FEATURE_PATTERN.match(stripped)
        if feat_match and feat_match.group(2):
            self._finalize_behave_scenario()
            self.current_feature_file = feat_match.group(2)
            self.current_node = None
            return

        # Check for Behave scenario header
        sc_match = BEHAVE_SCENARIO_PATTERN.match(stripped)
        if sc_match:
            self._finalize_behave_scenario()
            raw_title = sc_match.group(1).strip()
            title = re.sub(r"\s+--\s+@\d+\.\d+.*$", "", raw_title).strip()
            feat_file = sc_match.group(2) or self.current_feature_file or ""
            node_id = f"{feat_file}::{title}" if feat_file else title
            self.current_node = node_id
            self._ensure_node(node_id)
            self.method_outputs[node_id]["lines"].append(raw_line)
            return

        # Check for Pytest test method start line (e.g. "path/to/test.py::test_func ...")
        if not stripped.startswith(("=", "-", "rootdir:", "cachedir:", "plugins:")) and not clean.startswith("FAILURES"):
            node_id = _extract_pytest_node_id(clean)
            if node_id:
                self.current_node = node_id
                self._ensure_node(node_id)
                self.method_outputs[node_id]["lines"].append(raw_line)
                after_node = stripped[len(node_id) :]
                if re.search(r"(?:^|\s)(?:PASSED|XPASS)(?:\s+\[\s*\d+%\]|\b)", after_node):
                    self.method_outputs[node_id]["outcome"] = "passed"
                elif re.search(r"(?:^|\s)(?:FAILED|ERROR)(?:\s+\[\s*\d+%\]|\b)", after_node):
                    self.method_outputs[node_id]["outcome"] = "failed"
                elif re.search(r"(?:^|\s)(?:SKIPPED|XFAIL)(?:\s+\[\s*\d+%\]|\b)", after_node):
                    self.method_outputs[node_id]["outcome"] = "skipped"
                return

        # Check for Pytest FAILURES section demarcation
        if stripped == "FAILURES":
            self.in_failures_section = True
            self.current_node = None
            return

        if self.in_failures_section:
            fail_match = re.match(r"^_{3,}\s*(.*?)\s*_{3,}$", stripped)
            if fail_match:
                func_name = fail_match.group(1).strip()
                self.current_failure_node = None
                normalized_func = func_name.replace(".", "::")
                for n in self.method_outputs:
                    normalized_n = n.replace(".", "::")
                    if (
                        normalized_n.endswith(f"::{normalized_func}")
                        or normalized_n == normalized_func
                        or n.endswith(f"::{func_name}")
                        or n == func_name
                        or ("::" in normalized_n and normalized_n.split("::")[-1] == normalized_func.split("::")[-1])
                    ):
                        self.current_failure_node = n
                        self.method_outputs[n]["outcome"] = "failed"
                        break
                return
            if stripped.startswith("====="):
                self.in_failures_section = False
                self.current_failure_node = None
                return
            if self.current_failure_node:
                self.method_outputs[self.current_failure_node]["lines"].append(raw_line)
                return

        # Regular lines during test method execution
        if self.current_node and self.current_node in self.method_outputs:
            if stripped.startswith(("=====", "short test summary")):
                self.current_node = None
                return
            if ".feature::" in self.current_node and (
                re.match(r"^\d+\s+features?\s+passed", stripped)
                or stripped.startswith("Failing scenarios:")
            ):
                if self.method_outputs[self.current_node]["outcome"] == "unknown":
                    self.method_outputs[self.current_node]["outcome"] = "passed"
                self.current_node = None
                return
            self.method_outputs[self.current_node]["lines"].append(raw_line)
            self._accumulate_behave_step_duration(self.current_node, clean)
            if "PASSED" in clean and self.method_outputs[self.current_node]["outcome"] == "unknown":
                self.method_outputs[self.current_node]["outcome"] = "passed"
            elif (
                "FAILED" in clean
                or (
                    ".feature::" in self.current_node
                    and ("\x1b[31m" in raw_line or "Assertion Failed:" in clean or "Traceback (most recent call last):" in clean)
                )
            ):
                self.method_outputs[self.current_node]["outcome"] = "failed"
            elif "SKIPPED" in clean and self.method_outputs[self.current_node]["outcome"] == "unknown":
                self.method_outputs[self.current_node]["outcome"] = "skipped"

    def merge_json_report(self, report_data: dict[str, Any]) -> None:
        """Enriches recorded method outputs with durations and outcomes from pytest JSON report."""
        if not report_data or not isinstance(report_data, dict):
            return
        tests = report_data.get("tests", [])
        claimed_keys: set[str] = set()

        for t in tests:
            nid = t.get("nodeid", "")
            outcome = t.get("outcome", "unknown")

            # Sum execution duration across setup, call, and teardown stages
            total_dur = 0.0
            has_dur = False
            for stage in ("setup", "call", "teardown"):
                stage_data = t.get(stage)
                if isinstance(stage_data, dict) and "duration" in stage_data:
                    total_dur += float(stage_data["duration"])
                    has_dur = True
            if not has_dur and t.get("duration") is not None:
                total_dur = float(t["duration"])
                has_dur = True
            duration = round(total_dur, 4) if has_dur else None

            matched_key = None
            if nid in self.method_outputs and nid not in claimed_keys:
                matched_key = nid
            else:
                candidates = [
                    k
                    for k in self.method_outputs
                    if k not in claimed_keys and _is_same_test_node_at_path_boundary(k, nid)
                ]
                if candidates:
                    candidates.sort(key=lambda k: abs(len(k) - len(nid)))
                    matched_key = candidates[0]

            if not matched_key:
                self._ensure_node(nid)
                matched_key = nid
            elif len(nid) > len(matched_key):
                # Re-key to the more fully path-qualified node ID
                entry = self.method_outputs.pop(matched_key)
                entry["node_id"] = nid
                self.method_outputs[nid] = entry
                matched_key = nid

            claimed_keys.add(matched_key)
            self.method_outputs[matched_key]["outcome"] = outcome
            if duration is not None:
                self.method_outputs[matched_key]["duration"] = duration

            # Enrich method output with captured logs, prints, and failure tracebacks
            captured_sections = []
            for stage in ("setup", "call", "teardown"):
                stage_data = t.get(stage)
                if isinstance(stage_data, dict):
                    if stage_data.get("stdout"):
                        captured_sections.append(f"--- Captured stdout ({stage}) ---\n" + stage_data["stdout"].rstrip())
                    if stage_data.get("stderr"):
                        captured_sections.append(f"--- Captured stderr ({stage}) ---\n" + stage_data["stderr"].rstrip())
                    if stage_data.get("longrepr"):
                        captured_sections.append(f"--- Failure ({stage}) ---\n" + str(stage_data["longrepr"]).rstrip())

            if captured_sections:
                extra_text = "\n\n" + "\n\n".join(captured_sections) + "\n"
                curr_lines = "".join(self.method_outputs[matched_key]["lines"])
                # Avoid duplicating output if already streamed
                first_check = captured_sections[0][:35]
                if first_check not in curr_lines:
                    self.method_outputs[matched_key]["lines"].append(extra_text)

    def get_results(self) -> dict[str, Any]:
        """Returns normalized method outputs dictionary."""
        result = {}
        for nid, data in self.method_outputs.items():
            result[nid] = {
                "node_id": nid,
                "outcome": data["outcome"],
                "duration": data["duration"],
                "timestamp": data["timestamp"],
                "output": "".join(data["lines"]).strip(),
                "line_count": len(data["lines"]),
            }
        return result

