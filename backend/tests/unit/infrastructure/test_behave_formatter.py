import io
from unittest.mock import MagicMock

from behave.model_type import Status

from infrastructure.behave_formatter import AppendPrettyFormatter


class DummyStreamOpener:
    def __init__(self, stream):
        self.stream = stream

    def open(self):
        return self.stream


def test_append_pretty_formatter_initialization():
    """Verifies that AppendPrettyFormatter sets expected metadata and properties."""
    output = io.StringIO()
    mock_config = MagicMock()
    mock_config.show_source = True
    mock_config.show_timings = True
    mock_config.show_multiline = True

    formatter = AppendPrettyFormatter(DummyStreamOpener(output), mock_config)
    assert formatter.name == "append_pretty"
    assert "without overwriting via cursor-up" in formatter.description


def test_append_pretty_formatter_match_does_not_print_step():
    """Verifies that match() prints statement header but not the executing step line."""
    output = io.StringIO()
    mock_config = MagicMock()
    mock_config.show_source = True
    mock_config.show_timings = True
    mock_config.show_multiline = True

    formatter = AppendPrettyFormatter(DummyStreamOpener(output), mock_config)

    mock_match = MagicMock()
    mock_match.arguments = []
    mock_match.location = "features/steps/test.py:10"

    mock_step = MagicMock()
    mock_step.keyword = "Given"
    mock_step.name = "a precondition"
    mock_step.status = Status.passed
    mock_step.duration = 0.05
    formatter.steps = [mock_step]

    formatter.match(mock_match)
    # Output should not contain the step text prematurely
    assert "Given a precondition" not in output.getvalue()


def test_append_pretty_formatter_result_appends_without_cursor_up():
    """Verifies that result() outputs the step without cursor-up escape sequences."""
    output = io.StringIO()
    mock_config = MagicMock()
    mock_config.show_source = True
    mock_config.show_timings = True
    mock_config.show_multiline = True

    formatter = AppendPrettyFormatter(DummyStreamOpener(output), mock_config)

    mock_match = MagicMock()
    mock_match.arguments = []
    mock_match.location = "features/steps/test.py:10"

    mock_step = MagicMock()
    mock_step.keyword = "Given"
    mock_step.name = "a precondition"
    mock_step.status = Status.passed
    mock_step.duration = 0.05
    mock_step.error_message = None
    mock_step.text = None
    mock_step.table = None

    formatter.steps = [mock_step]
    formatter.match(mock_match)
    formatter.result(mock_step)

    rendered = output.getvalue()
    assert "Given" in rendered
    assert "a precondition" in rendered
    # Must NOT have ANSI cursor-up escape code \x1b[{n}A
    assert "\x1b[" not in rendered or "A" not in [c for c in rendered if c == "A" and "\x1b[" in rendered]
    assert not any(f"\x1b[{i}A" in rendered for i in range(1, 10))


def test_append_pretty_formatter_result_prints_error_message():
    """Verifies that result() formats and prints step error messages on failure."""
    output = io.StringIO()
    mock_config = MagicMock()
    mock_config.show_source = True
    mock_config.show_timings = True
    mock_config.show_multiline = True

    formatter = AppendPrettyFormatter(DummyStreamOpener(output), mock_config)

    mock_match = MagicMock()
    mock_match.arguments = []
    mock_match.location = "features/steps/test.py:20"

    mock_step = MagicMock()
    mock_step.keyword = "When"
    mock_step.name = "an action fails"
    mock_step.status = Status.failed
    mock_step.duration = 0.02
    mock_step.error_message = "AssertionError: Something went wrong"
    mock_step.text = None
    mock_step.table = None

    formatter.steps = [mock_step]
    formatter.match(mock_match)
    formatter.result(mock_step)

    rendered = output.getvalue()
    assert "When" in rendered
    assert "an action fails" in rendered
    assert "AssertionError: Something went wrong" in rendered
    assert not any(f"\x1b[{i}A" in rendered for i in range(1, 10))
