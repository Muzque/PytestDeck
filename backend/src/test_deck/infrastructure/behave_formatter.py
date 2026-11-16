import json
import os
import re

from behave.formatter.pretty import PrettyFormatter
from behave.textutil import indent

EVENT_PREFIX = "__PYTESTDECK_EVENT__:"
SCENARIO_OUTLINE_SUFFIX = re.compile(r"\s+--\s+@\d+\.\d+.*$")


class AppendPrettyFormatter(PrettyFormatter):
    """Behave formatter that streams and appends steps sequentially without cursor-up overwrites.

    Inherits from PrettyFormatter to keep full ANSI coloring, timing, source location,
    and multiline tables/docstrings, but avoids printing intermediate 'executing' steps
    that would otherwise trigger cursor-up ANSI escape sequences.
    """

    name = "append_pretty"
    description = "Pretty formatter that appends steps sequentially without overwriting via cursor-up"

    def __init__(self, stream_opener, config):
        super().__init__(stream_opener, config)
        self._scenario_outcomes: dict[str, str] = {}
        self._scenario_durations: dict[str, float] = {}
        self._emit_events: bool = os.environ.get("PYTESTDECK_RUNNER") == "1"


    def match(self, match):
        """Invoked when a step is matched.

        Outputs the scenario statement (if not yet output) and flushes the stream,
        without printing the executing step line prematurely.
        """
        self._match = match
        self.print_statement()
        self.stream.flush()

    def indented_text(self, text, proceed):
        """Calculates indentation spacing for comments and locations safely."""
        if not text:
            return ""
        if self.indentations:
            if proceed:
                indentation = self.indentations.pop(0)
            else:
                indentation = self.indentations[0]
        else:
            indentation = 2
        return f"{' ' * indentation} # {text}"

    def result(self, step):
        """Invoked after a step has executed.

        Prints the final step outcome, status color, and execution duration without
        using cursor-up escapes, so preceding steps and streaming logger outputs are preserved.
        """
        arguments = []
        location = None
        if self._match:
            arguments = self._match.arguments
            location = self._match.location

        self.print_step(step.status, arguments, location, proceed=True)

        if step.error_message:
            self.stream.write(indent(step.error_message.strip(), "      "))
            self.stream.write("\n\n")

        self.stream.flush()

    def _finish_current_scenario(self):
        """Emits a structured PytestDeck status event for the completed scenario before finalizing."""
        scenario = getattr(self, "current_scenario", None)
        if scenario is not None:
            try:
                raw_name = str(getattr(scenario, "name", "") or "").strip()
                clean_title = SCENARIO_OUTLINE_SUFFIX.sub("", raw_name).strip()
                location = getattr(scenario, "location", None)
                feat_file = str(getattr(location, "filename", "") or "").strip()
                node_id = f"{feat_file}::{clean_title}" if feat_file and clean_title else clean_title

                status_obj = getattr(scenario, "status", None)
                status_name = str(getattr(status_obj, "name", status_obj) or "").lower()
                if status_name in ("failed", "error", "undefined", "hook_error"):
                    row_outcome = "failed"
                elif status_name in ("skipped", "untested"):
                    row_outcome = "skipped"
                else:
                    row_outcome = "passed"

                prev_outcome = self._scenario_outcomes.get(node_id)
                if prev_outcome == "failed" or row_outcome == "failed":
                    final_outcome = "failed"
                elif row_outcome == "passed" or prev_outcome == "passed":
                    final_outcome = "passed"
                else:
                    final_outcome = row_outcome
                self._scenario_outcomes[node_id] = final_outcome

                dur_val = getattr(scenario, "duration", None)
                if isinstance(dur_val, (int, float)):
                    self._scenario_durations[node_id] = round(
                        self._scenario_durations.get(node_id, 0.0) + float(dur_val), 4
                    )
                total_dur = self._scenario_durations.get(node_id)

                if node_id and self._emit_events:
                    payload = json.dumps(
                        {
                            "node_id": node_id,
                            "outcome": final_outcome,
                            "duration": total_dur,
                        },
                        separators=(",", ":"),
                    )
                    self.stream.write(f"{EVENT_PREFIX}{payload}\n")
                    self.stream.flush()
            except Exception:
                pass

        super()._finish_current_scenario()

