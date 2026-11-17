import sys

# 1. Minimaliste
BANNER_MINIMAL = "zipr ▸ parallel zip"

# 2. Compact (3 lignes, Unicode)
BANNER_COMPACT = r"""
╔═╗╦╔═╗╦═╗
╔═╝║╠═╝╠╦╝
╚═╝╩╩  ╩╚═
""".strip("\n")

# 3. Full size (10 lignes, Unicode)
BANNER_FULL_SIZE = r"""
==================================
     _____ ___ ____  ____
    |__  /|_ _|  _ \|  _ \
      / /  | || |_) | |_) |
     / /_  | ||  __/|  _ /
    /____||___|_|   |_| \_\

  parallel zip · multi-threaded

==================================
"""


def banner(printable: bool = False) -> None:
    """Print the banner to stderr, keeping stdout free for data."""
    if printable:
        print(BANNER_FULL_SIZE, file=sys.stderr)
