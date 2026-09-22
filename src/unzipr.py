import sys
import zipfile
from pathlib import Path

from isal import isal_zlib

# from concurrent.futures import ThreadPoolExecutor, as_completed
from .design.banner import banner
from .utils import arg_parser as parser
from .utils import logger


def main() -> None:
    args = parser.parse_unzip_args()

    banner(args.verbose or args.debug)

    if args.threads == 1:
        logger.info("Using a single thread for zipping.", args.verbose or args.debug)
        zipfile.zlib = isal_zlib

    with zipfile.ZipFile(
        args.input,
        "r",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=isal_zlib.ISAL_BEST_COMPRESSION,
    ) as zipf:
        safe_extract_all(zipf, args.output)

    logger.info(
        f"Successfully extracted the zip file to {args.output}",
        args.verbose or args.debug,
    )


def safe_extract_all(zipf: zipfile.ZipFile, destination: str) -> None:
    destination_path = Path(destination).resolve()

    for member in zipf.infolist():
        target_path = (destination_path / member.filename).resolve()

        if (
            target_path != destination_path
            and destination_path not in target_path.parents
        ):
            logger.error(f"Unsafe path in ZIP archive: {member.filename}")

        logger.debug(f"Extracting {member.filename} to {target_path}", True)
        zipf.extract(member, destination_path)


if __name__ == "__main__":
    sys.exit(main())
