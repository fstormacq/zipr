import argparse
import os
import sys
import zipfile

from . import logger

DEFAULT_THREADS = 1


def parse_zip_args():
    parser = argparse.ArgumentParser(
        description="zip, but it actually uses all your cores."
    )

    parser.add_argument("input", type=str, help="Input file or directory to be zipped.")

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file or directory for the zipped content. (Default: <input_value>.zip)",
    )

    parser.add_argument(
        "--threads",
        "-t",
        type=int,
        help="Number of threads to use for zipping. (Default: 4)",
        default=DEFAULT_THREADS,
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    parser.add_argument("--debug", action="store_true", help="Enable debug output.")

    args = parser.parse_args()
    check_cli_args(args)

    return args


def parse_unzip_args():
    parser = argparse.ArgumentParser(
        description="unzip, but it actually uses all your cores."
    )

    parser.add_argument("input", type=str, help="Input zip file to be unzipped.")

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory for the unzipped content. (Default: <input_value>)",
    )

    parser.add_argument(
        "--threads",
        "-t",
        type=int,
        help="Number of threads to use for unzipping. (Default: 4)",
        default=DEFAULT_THREADS,
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")

    parser.add_argument("--debug", action="store_true", help="Enable debug output.")

    args = parser.parse_args()
    check_cli_args(args, require_zip=True)

    return args


def check_cli_args(args: argparse.Namespace, require_zip: bool = False) -> None:
    """
    Checks the command-line arguments for validity.
    """

    _validate_input_path(args.input, require_zip)
    args.output = _get_output_path(args, require_zip)
    _prepare_output(args)
    args.threads = _normalize_threads(args.threads)

    logger.debug(f"CLI arguments: {args}", args.debug)


def _validate_input_path(input_path: str, require_zip: bool = False) -> None:
    if not os.path.exists(input_path):
        logger.error(f"Input file or directory '{input_path}' does not exist.")
        sys.exit(1)

    if require_zip and (
        not os.path.isfile(input_path) or not zipfile.is_zipfile(input_path)
    ):
        logger.error(f"Input file '{input_path}' is not a valid ZIP archive.")
        sys.exit(1)


def _get_output_path(args: argparse.Namespace, require_zip: bool = False) -> str | None:
    if args.output is not None:
        return args.output

    if require_zip:
        base_name, _ = os.path.splitext(args.input)
        output = f"{base_name}"
    elif os.path.isdir(args.input):
        output = f"{args.input.rstrip(os.sep)}.zip"
    elif os.path.isfile(args.input):
        base_name, _ = os.path.splitext(args.input)
        output = f"{base_name}.zip"
    else:
        logger.error(f"Input path '{args.input}' is neither a file nor a directory.")
        sys.exit(1)

    logger.info(
        f"No output specified. Using default output: '{output}'",
        args.verbose,
    )
    return output


def _prepare_output(args: argparse.Namespace) -> None:
    if not args.output:
        return

    output_dir = os.path.dirname(args.output)
    if output_dir:
        logger.debug(f"Creating output directory: {output_dir}", args.verbose)
        os.makedirs(output_dir, exist_ok=True)

    if os.path.exists(args.output):
        logger.warn(f"Output file '{args.output}' already exists.")

        response = input("Do you want to overwrite it? (y/n): ").strip().lower()

        if response != "y":
            logger.info("Operation cancelled by the user.", args.verbose)
            sys.exit(0)

        logger.info(f"Overwriting '{args.output}'.", args.verbose)


def _normalize_threads(thread_count: int | None) -> int | None:
    if thread_count is None:
        return None

    available_threads = os.cpu_count() or 1

    if thread_count < 1:
        logger.warn("Number of threads must be at least 1. Setting value to 1.")
        return 1

    if thread_count > available_threads:
        logger.warn(
            f"Number of threads cannot exceed the number of logical CPUs ({available_threads}). Setting value to {available_threads}."
        )
        return available_threads

    return thread_count
