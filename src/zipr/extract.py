import zipfile
from pathlib import Path

from .errors import ZiprError
from .log import log


def extract_archive(archive_path: str, destination: str) -> None:
    """Extract archive_path into destination after validating every member."""
    destination_path = Path(destination).resolve()

    with zipfile.ZipFile(archive_path) as zipf:
        members = zipf.infolist()
        _check_members(members, destination_path)

        for member in members:
            log.debug("Extracting %s", member.filename)
            zipf.extract(member, destination_path)


def _check_members(members: list[zipfile.ZipInfo], destination: Path) -> None:
    """
    Refuse the whole archive before writing anything, so a malicious archive
    never leaves a partial extraction behind.
    """
    unsafe_members = [
        member.filename
        for member in members
        if not _is_within(destination / member.filename, destination)
    ]
    if unsafe_members:
        raise ZiprError(f"Unsafe path(s) in ZIP archive: {', '.join(unsafe_members)}")


def _is_within(path: Path, directory: Path) -> bool:
    resolved = path.resolve()
    return resolved == directory or directory in resolved.parents
