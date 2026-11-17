import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

from .errors import ZiprError
from .log import log


def extract_archive(archive_path: str, destination: str) -> None:
    """Extract archive_path into destination after validating every member."""
    destination_path = Path(destination).resolve()

    with zipfile.ZipFile(archive_path) as zipf:
        members = zipf.infolist()
        _check_members(zipf, members, destination_path)

        links = []
        directories = []
        for member in members:
            if _is_symlink(member):
                links.append(member)
                continue

            log.debug("Extracting %s", member.filename)
            path = zipf.extract(member, destination_path)
            if member.is_dir():
                directories.append((member, path))
            else:
                _restore_mode(member, path)

        # Links come after regular files so nothing is ever written through
        # one of them.
        for member in links:
            log.debug("Linking %s", member.filename)
            _create_symlink(zipf, member, destination_path)

        # Directory modes go last, children before parents, so a read-only or
        # non-searchable directory never blocks what happens inside it.
        for member, path in reversed(directories):
            _restore_mode(member, path)


def _check_members(
    zipf: zipfile.ZipFile, members: list[zipfile.ZipInfo], destination: Path
) -> None:
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

    links = {
        member.filename.rstrip("/"): member for member in members if _is_symlink(member)
    }

    unsafe_links = []
    for name, member in links.items():
        target = _read_link_target(zipf, member)
        if not _is_safe_link_target(name, target, destination):
            unsafe_links.append(f"{name} -> {target}")
    if unsafe_links:
        raise ZiprError(f"Unsafe link(s) in ZIP archive: {', '.join(unsafe_links)}")

    nested_members = [
        member.filename
        for member in members
        if any(
            str(parent) in links for parent in PurePosixPath(member.filename).parents
        )
    ]
    if nested_members:
        raise ZiprError(
            f"Member(s) stored below a link in ZIP archive: {', '.join(nested_members)}"
        )


def _is_within(path: Path, directory: Path) -> bool:
    resolved = path.resolve()
    return resolved == directory or directory in resolved.parents


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    return member.create_system == 3 and stat.S_ISLNK(member.external_attr >> 16)


def _read_link_target(zipf: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    return zipf.read(member).decode("utf-8")


def _is_safe_link_target(name: str, target: str, destination: Path) -> bool:
    if not target or os.path.isabs(target):
        return False
    link_directory = (destination / name).parent
    return _is_within(link_directory / target, destination)


def _create_symlink(
    zipf: zipfile.ZipFile, member: zipfile.ZipInfo, destination: Path
) -> None:
    path = destination / member.filename.rstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        raise ZiprError(f"Cannot replace directory '{path}' with a link.")
    os.symlink(_read_link_target(zipf, member), path)


def _restore_mode(member: zipfile.ZipInfo, path: str) -> None:
    """Apply the stored rwx bits; setuid, setgid and sticky are dropped."""
    mode = (member.external_attr >> 16) & 0o777
    if member.create_system == 3 and mode:
        os.chmod(path, mode)
