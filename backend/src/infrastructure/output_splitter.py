import datetime
import re
from typing import Any

ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PYTEST_NODE_PATTERN = re.compile(r"([a-zA-Z0-9_\-\./\\]+\.py::[a-zA-Z0-9_\-\.\[\]:]+)")
BEHAVE_SCENARIO_PATTERN = re.compile(r"^(?:Scenario|Scenario Outline):\s*(.*?)(?:\s+#\s*([^\s:]+\.feature)(?::\d+)?)?$")
BEHAVE_FEATURE_PATTERN = re.compile(r"^Feature:\s*(.*?)(?:\s+#\s*([^\s:]+\.feature)(?::\d+)?)?$")


class MethodOutputCollector:
    """Collects, segments, and attributes console output lines to individual test methods and scenarios."""

    def __init__(self, requested_nodes: list[str] | None = None):
        self.requested_nodes = requested_nodes or []
        self.is_single_node = len(self.requested_nodes) == 1 and "::" in self.requested_nodes[0]
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


    def process_line(self, raw_line: str) -> None:
        """Processes a single streamed stdout line, segmenting output by test method boundaries."""
        clean = ANSI_ESCAPE.sub("", raw_line).rstrip("\r\n")
        stripped = clean.strip()

        # If a single targeted method is executed, attribute all process lines to it
        if self.is_single_node and self.single_node_id:
            self.method_outputs[self.single_node_id]["lines"].append(raw_line)
            if "PASSED" in clean and self.method_outputs[self.single_node_id]["outcome"] == "unknown":
                self.method_outputs[self.single_node_id]["outcome"] = "passed"
            elif "FAILED" in clean:
                self.method_outputs[self.single_node_id]["outcome"] = "failed"
            elif "SKIPPED" in clean and self.method_outputs[self.single_node_id]["outcome"] == "unknown":
                self.method_outputs[self.single_node_id]["outcome"] = "skipped"
            return

        # Check for Behave feature header
        feat_match = BEHAVE_FEATURE_PATTERN.match(stripped)
        if feat_match and feat_match.group(2):
            self.current_feature_file = feat_match.group(2)
            return

        # Check for Behave scenario header
        sc_match = BEHAVE_SCENARIO_PATTERN.match(stripped)
        if sc_match:
            title = sc_match.group(1).strip()
            feat_file = sc_match.group(2) or self.current_feature_file or ""
            node_id = f"{feat_file}::{title}" if feat_file else title
            self.current_node = node_id
            self._ensure_node(node_id)
            self.method_outputs[node_id]["lines"].append(raw_line)
            return

        # Check for Pytest test method start line (e.g. "path/to/test.py::test_func ...")
        if not stripped.startswith(("=", "-", "rootdir:", "cachedir:", "plugins:")):
            py_match = PYTEST_NODE_PATTERN.search(clean)
            if py_match and not clean.startswith("FAILURES"):
                node_id = py_match.group(1)
                self.current_node = node_id
                self._ensure_node(node_id)
                self.method_outputs[node_id]["lines"].append(raw_line)
                if "PASSED" in clean:
                    self.method_outputs[node_id]["outcome"] = "passed"
                elif "FAILED" in clean:
                    self.method_outputs[node_id]["outcome"] = "failed"
                elif "SKIPPED" in clean:
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
                for n in self.method_outputs:
                    if n.endswith(f"::{func_name}") or n == func_name:
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
            self.method_outputs[self.current_node]["lines"].append(raw_line)
            if "PASSED" in clean and self.method_outputs[self.current_node]["outcome"] == "unknown":
                self.method_outputs[self.current_node]["outcome"] = "passed"
            elif "FAILED" in clean:
                self.method_outputs[self.current_node]["outcome"] = "failed"
            elif "SKIPPED" in clean and self.method_outputs[self.current_node]["outcome"] == "unknown":
                self.method_outputs[self.current_node]["outcome"] = "skipped"

    def merge_json_report(self, report_data: dict[str, Any]) -> None:
        """Enriches recorded method outputs with durations and outcomes from pytest JSON report."""
        if not report_data or not isinstance(report_data, dict):
            return
        tests = report_data.get("tests", [])
        for t in tests:
            nid = t.get("nodeid", "")
            outcome = t.get("outcome", "unknown")
            duration = t.get("call", {}).get("duration") or t.get("duration")

            matched_key = None
            if nid in self.method_outputs:
                matched_key = nid
            else:
                for k in self.method_outputs:
                    if k.endswith(nid) or nid.endswith(k):
                        matched_key = k
                        break

            if matched_key:
                self.method_outputs[matched_key]["outcome"] = outcome
                if duration is not None:
                    self.method_outputs[matched_key]["duration"] = round(float(duration), 3)

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
