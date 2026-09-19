import argparse
import os
import sys

from . import logger

DEFAULT_THREADS = 4


def parse_args():
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


def check_cli_args(args: argparse.Namespace) -> None:
    """
    Checks the command-line arguments for validity.
    """

    if not os.path.exists(args.input):
        logger.error(f"Input file or directory '{args.input}' does not exist.")
        sys.exit(1)

    if args.output is None:
        if os.path.isdir(args.input):
            args.output = f"{args.input.rstrip(os.sep)}.zip"

        elif os.path.isfile(args.input):
            base_name, _ = os.path.splitext(args.input)
            args.output = f"{base_name}.zip"

        if args.output:
            logger.info(
                f"No output specified. Using default output: '{args.output}'",
                args.verbose,
            )

    if args.output:
        output_dir = os.path.dirname(args.output)
        os.makedirs(output_dir, exist_ok=True)

        if os.path.exists(args.output):
            logger.warn(f"Output file '{args.output}' already exists.")

            response = input("Do you want to overwrite it? (y/n): ").strip().lower()

            if response != "y":
                logger.info("Operation cancelled by the user.", args.verbose)
                sys.exit(0)

            logger.info(f"Overwriting '{args.output}'.", args.verbose)

    if args.threads is not None:
        available_threads = os.cpu_count()

        if args.threads < 1:
            logger.warn("Number of threads must be at least 1. Setting value to 1.")
            args.threads = 1

        elif args.threads > available_threads:
            logger.warn(
                f"Number of threads cannot exceed the number of logical CPUs ({available_threads}). Setting value to {available_threads}."
            )
            args.threads = available_threads

    logger.debug(f"CLI arguments: {args}", args.debug)
