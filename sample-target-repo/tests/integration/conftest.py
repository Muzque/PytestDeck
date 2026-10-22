import logging

import pytest


class ColoredFormatter(logging.Formatter):
    """Custom formatter to colorize log levels with ANSI escape codes."""

    COLORS = {
        "DEBUG": "\x1b[36m",    # Cyan
        "INFO": "\x1b[32m",     # Green
        "WARNING": "\x1b[33m",  # Yellow
        "ERROR": "\x1b[31m",    # Red
        "CRITICAL": "\x1b[35m", # Magenta
    }
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        orig_levelname = record.levelname
        color = self.COLORS.get(orig_levelname, "")
        if color:
            record.levelname = f"{color}{orig_levelname:<10}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = orig_levelname


def pytest_configure(config: pytest.Config) -> None:
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    if logging_plugin and hasattr(logging_plugin, "log_cli_handler") and logging_plugin.log_cli_handler:
        datefmt = config.getini("log_cli_date_format") or "%H:%M:%S"
        fmt = config.getini("log_cli_format") or "%(asctime)s %(levelname)s - %(message)s"
        # Avoid double padding if levelname has ANSI padding
        fmt = fmt.replace("%(levelname)-10s", "%(levelname)s")
        logging_plugin.log_cli_handler.setFormatter(ColoredFormatter(fmt=fmt, datefmt=datefmt))
