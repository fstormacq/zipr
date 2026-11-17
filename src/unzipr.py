import sys
import zipfile
from pathlib import Path

from isal import isal_zlib

from .design.banner import banner
from .utils import arg_parser as parser
from .utils import logger


def main() -> None:
    args = parser.parse_unzip_args()

    banner(args.verbose or args.debug)

    zipfile.zlib = isal_zlib

    with zipfile.ZipFile(args.input, "r") as zipf:
        safe_extract_all(zipf, args.output, args.debug)

    logger.info(
        f"Successfully extracted the zip file to {args.output}",
        args.verbose or args.debug,
    )


def safe_extract_all(zipf: zipfile.ZipFile, destination: str, debug: bool) -> None:
    destination_path = Path(destination).resolve()
    members = zipf.infolist()

    # Validate every member before writing anything, so a malicious archive
    # never leaves a partial extraction behind.
    unsafe_members = [
        member.filename
        for member in members
        if not _is_within(destination_path / member.filename, destination_path)
    ]
    if unsafe_members:
        logger.error(f"Unsafe path(s) in ZIP archive: {', '.join(unsafe_members)}")

    for member in members:
        logger.debug(f"Extracting {member.filename} to {destination_path}", debug)
        zipf.extract(member, destination_path)


def _is_within(path: Path, directory: Path) -> bool:
    resolved = path.resolve()
    return resolved == directory or directory in resolved.parents


if __name__ == "__main__":
    sys.exit(main())
