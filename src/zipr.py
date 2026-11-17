import contextlib
import os
import sys
import tempfile
import zipfile

from isal import isal_zlib

from .design.banner import banner
from .utils import arg_parser as parser
from .utils import logger


def main() -> None:
    args = parser.parse_zip_args()

    banner(args.verbose or args.debug)

    zipfile.zlib = isal_zlib

    output_path = os.path.abspath(args.output)
    tmp_path = create_temp_file(output_path)
    excluded_paths = {os.path.realpath(output_path), os.path.realpath(tmp_path)}

    try:
        write_archive(args, tmp_path, excluded_paths)
        os.replace(tmp_path, output_path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp_path)
        raise

    logger.info(
        f"Successfully created the zip file at {args.output}",
        args.verbose or args.debug,
    )


def create_temp_file(output_path: str) -> str:
    """Create the temporary archive next to the output so os.replace is atomic."""
    fd, tmp_path = tempfile.mkstemp(
        prefix=".zipr-", suffix=".tmp", dir=os.path.dirname(output_path)
    )
    os.close(fd)

    # mkstemp creates the file with 0600, restore the usual umask-based mode.
    umask = os.umask(0)
    os.umask(umask)
    os.chmod(tmp_path, 0o666 & ~umask)

    return tmp_path


def write_archive(args, archive_path: str, excluded_paths: set[str]) -> None:
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=isal_zlib.ISAL_BEST_COMPRESSION,
    ) as zipf:
        if os.path.isfile(args.input):
            base_dir = os.path.dirname(os.path.abspath(args.input))
            files_to_zip = [(base_dir, [], [os.path.basename(args.input)])]
        else:
            base_dir = args.input
            files_to_zip = os.walk(args.input)

        for root, _, files in files_to_zip:
            logger.debug(f"Walking through directory: {root}", args.debug)
            for filename in files:
                file_path = os.path.join(root, filename)
                if os.path.realpath(file_path) in excluded_paths:
                    logger.debug(f"Skipping output archive: {file_path}", args.debug)
                    continue

                logger.debug(f"Adding file: {filename}", args.debug)
                archive_name = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, archive_name)


if __name__ == "__main__":
    sys.exit(main())
