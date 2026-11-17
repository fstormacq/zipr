"""
Logging setup that mirrors the ANSI visual identity of the shell scripts.

  ◆  debug   - blue, dimmed message
  ℹ  info    - cyan
  ⚠  warning - yellow
  ✖  error   - red

Everything goes to stderr so stdout stays free for data.
"""

import logging
import os
import sys

RST = "\033[0m"
DIM = "\033[2m"

RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"

_STYLES = {
    logging.DEBUG: (BLUE, "◆"),
    logging.INFO: (CYAN, "ℹ"),
    logging.WARNING: (YELLOW, "⚠"),
    logging.ERROR: (RED, "✖"),
}

log = logging.getLogger("zipr")


class _Formatter(logging.Formatter):
    def __init__(self, use_color: bool) -> None:
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        color, symbol = _STYLES.get(record.levelno, (RED, "✖"))
        message = record.getMessage()
        if not self.use_color:
            return f"{symbol}  {message}"
        if record.levelno == logging.DEBUG:
            message = f"{DIM}{message}{RST}"
        return f"{color}{symbol}{RST}  {message}"


def use_color(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    stream = sys.stderr
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_Formatter(use_color(stream)))

    log.handlers[:] = [handler]
    log.propagate = False
    if debug:
        log.setLevel(logging.DEBUG)
    elif verbose:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.WARNING)
