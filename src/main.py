import os
import sys
import zipfile

from isal import isal_zlib

# from concurrent.futures import ThreadPoolExecutor, as_completed
from .design import banner
from .utils import arg_parser as parser
from .utils import logger


def main() -> None:
    print(banner.BANNER_FULL_SIZE)

    args = parser.parse_args()

    if args.threads == 1:
        logger.info("Using a single thread for zipping.", args.verbose or args.debug)
        zipfile.zlib = isal_zlib

    with zipfile.ZipFile(
        args.output,
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
                logger.debug(f"Adding file: {filename}", args.debug)
                file_path = os.path.join(root, filename)
                archive_name = os.path.relpath(file_path, base_dir)
                zipf.write(file_path, archive_name)

    logger.info(f"Successfully created the zip file at {args.output}", True)


if __name__ == "__main__":
    sys.exit(main())
