import logging


class ColoredFormatter(logging.Formatter):
    """Logging formatter that colors the log levelname according to severity."""

    COLORS = {
        logging.DEBUG: "\x1b[36m",       # Cyan
        logging.INFO: "\x1b[32m",        # Green
        logging.WARNING: "\x1b[33m",     # Yellow
        logging.ERROR: "\x1b[31m",       # Red
        logging.CRITICAL: "\x1b[1;31m",  # Bold Red
    }
    RESET = "\x1b[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, self.RESET)
        record_copy = logging.makeLogRecord(record.__dict__)
        record_copy.levelname = f"{color}{record.levelname:<10}{self.RESET}"
        return super().format(record_copy)


def before_all(context):
    """Configures colored logging for Behave test runs."""
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt="%(asctime)s %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
