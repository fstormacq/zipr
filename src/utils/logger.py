"""
Logging helpers that mirror the ANSI visual identity of the shell scripts.

  ℹ  info   - cyan
  ✔  ok     - green
  ⚠  warn   - yellow
  ✖  error  - red
     dim    - dimmed
     header - bold section title with a dim separator
"""

RST = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"


def info(msg: str, verbose: bool = False) -> None:
    if verbose:
        print(f"{CYAN}ℹ{RST}  {msg}")


def warn(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"{YELLOW}⚠{RST}  {msg}")


def error(msg: str, verbose: bool = True) -> None:
    if verbose:
        print(f"{RED}✖{RST}  {msg}")


def dim(msg: str, verbose: bool = False) -> None:
    if verbose:
        print(f"{DIM}{msg}{RST}")


def header(msg: str, verbose: bool = False) -> None:
    """Print a bold section title followed by a dim separator line."""
    if verbose:
        print(f"\n{BOLD}{msg}{RST}")
        print(f"{DIM}{'─' * len(msg)}{RST}")


def debug(msg: str, debug: bool = False) -> None:
    if debug:
        print(f"{BLUE}◆{RST}  {DIM}{msg}{RST}")
