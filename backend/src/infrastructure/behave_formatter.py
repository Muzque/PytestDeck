from behave.formatter.pretty import PrettyFormatter
from behave.textutil import indent


class AppendPrettyFormatter(PrettyFormatter):
    """Behave formatter that streams and appends steps sequentially without cursor-up overwrites.

    Inherits from PrettyFormatter to keep full ANSI coloring, timing, source location,
    and multiline tables/docstrings, but avoids printing intermediate 'executing' steps
    that would otherwise trigger cursor-up ANSI escape sequences.
    """

    name = "append_pretty"
    description = "Pretty formatter that appends steps sequentially without overwriting via cursor-up"

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
