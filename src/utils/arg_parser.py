import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="zip, but it actually uses all your cores."
    )

    parser.add_argument("input", type=str, help="Input file or directory to be zipped.")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    parser.add_argument("--debug", action="store_true", help="Enable debug output.")

    return parser.parse_args()
