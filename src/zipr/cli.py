import argparse
import os
import re
import sys
import zipfile
from collections.abc import Callable

from .archive import COMPRESSION_LEVELS, DEFAULT_COMPRESSION_LEVEL, create_archive
from .banner import banner
from .errors import ZiprError
from .extract import extract_archive
from .log import log, setup_logging


def zip_main(argv: list[str] | None = None) -> int:
    return _run(parse_zip_args(argv), _zip)


def unzip_main(argv: list[str] | None = None) -> int:
    return _run(parse_unzip_args(argv), _unzip)


def _run(args: argparse.Namespace, action: Callable[[argparse.Namespace], int]) -> int:
    setup_logging(args.verbose, args.debug)
    banner(args.verbose or args.debug)
    log.debug("CLI arguments: %s", args)

    try:
        return action(args)
    except ZiprError as error:
        log.error("%s", error)
        return 1
    except KeyboardInterrupt:
        log.error("Interrupted.")
        return 130


def _zip(args: argparse.Namespace) -> int:
    validate_zip_input(args.input)
    output = args.output or default_zip_output(args.input)
    threads = normalize_threads(args.threads)
    log.debug("Using %d thread(s).", threads)

    if not confirm_overwrite(output, args.force):
        log.info("Operation cancelled by the user.")
        return 0

    create_archive(args.input, output, level=args.level)
    log.info("Successfully created the zip file at %s", output)
    return 0


def _unzip(args: argparse.Namespace) -> int:
    validate_unzip_input(args.input)
    output = args.output or default_unzip_output(args.input)
    threads = normalize_threads(args.threads)
    log.debug("Using %d thread(s).", threads)

    if not confirm_overwrite(output, args.force):
        log.info("Operation cancelled by the user.")
        return 0

    extract_archive(args.input, output, max_size=args.max_size)
    log.info("Successfully extracted the zip file to %s", output)
    return 0


# ── Argument parsing ─────────────────────────────────────────────────────────


def parse_zip_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _base_parser(
        prog="zipr",
        description="zip, but it actually uses all your cores.",
        input_help="Input file or directory to be zipped.",
        output_help="Output ZIP file. (Default: <input>.zip)",
    )
    parser.add_argument(
        "--level",
        "-l",
        type=int,
        choices=COMPRESSION_LEVELS,
        default=DEFAULT_COMPRESSION_LEVEL,
        help="ISA-L compression level, from 0 (fastest) to 3 (smallest). "
        "(Default: %(default)s)",
    )
    return parser.parse_args(argv)


def parse_unzip_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = _base_parser(
        prog="unzipr",
        description="unzip, but it actually uses all your cores.",
        input_help="Input ZIP file to be unzipped.",
        output_help="Output directory. (Default: <input> without extension)",
    )
    parser.add_argument(
        "--max-size",
        type=parse_size,
        help="Refuse archives expanding to more than this size, e.g. 500M or 2G. "
        "(Default: free space on the destination disk)",
    )
    return parser.parse_args(argv)


def _base_parser(
    prog: str, description: str, input_help: str, output_help: str
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    parser.add_argument("input", help=input_help)
    parser.add_argument("--output", "-o", help=output_help)
    parser.add_argument(
        "--threads",
        "-t",
        type=_positive_int,
        default=os.cpu_count() or 1,
        help="Number of threads to use. (Default: number of logical CPUs)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite the output without asking for confirmation.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--debug", action="store_true", help="Enable debug output.")
    return parser


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return number


_SIZE_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}


def parse_size(value: str) -> int:
    """Parse a human size such as 512, 500M, 1.5G or 2GiB (powers of 1024)."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMGT]?)(?:i?B)?", value.strip(), re.I)
    if not match:
        raise argparse.ArgumentTypeError(f"invalid size: {value!r}")
    number, unit = match.groups()
    return int(float(number) * _SIZE_UNITS[unit.upper()])


# ── Validation ───────────────────────────────────────────────────────────────


def validate_zip_input(input_path: str) -> None:
    if not os.path.exists(input_path):
        raise ZiprError(f"Input file or directory '{input_path}' does not exist.")


def validate_unzip_input(input_path: str) -> None:
    if not os.path.isfile(input_path) or not zipfile.is_zipfile(input_path):
        raise ZiprError(f"Input file '{input_path}' is not a valid ZIP archive.")


def default_zip_output(input_path: str) -> str:
    if os.path.isfile(input_path):
        base_name, _ = os.path.splitext(input_path)
        return f"{base_name}.zip"

    input_dir = os.path.abspath(input_path)
    name = os.path.basename(input_dir)
    if not name:
        raise ZiprError(
            f"Cannot derive an archive name from '{input_path}'. Use --output."
        )
    return os.path.join(os.path.dirname(input_dir), f"{name}.zip")


def default_unzip_output(input_path: str) -> str:
    base_name, _ = os.path.splitext(input_path)
    return base_name


def normalize_threads(threads: int) -> int:
    available_threads = os.cpu_count() or 1
    if threads > available_threads:
        log.warning(
            "Number of threads cannot exceed the number of logical CPUs (%d). "
            "Setting value to %d.",
            available_threads,
            available_threads,
        )
        return available_threads
    return threads


# ── Side effects ─────────────────────────────────────────────────────────────


def confirm_overwrite(output: str, force: bool) -> bool:
    """Return True when output may be written, asking the user if needed."""
    if not os.path.exists(output) or force:
        return True

    if not sys.stdin.isatty():
        raise ZiprError(
            f"Output '{output}' already exists. Use --force to overwrite it."
        )

    log.warning("Output '%s' already exists.", output)
    print("Do you want to overwrite it? (y/n): ", end="", file=sys.stderr, flush=True)
    response = sys.stdin.readline().strip().lower()
    return response == "y"
