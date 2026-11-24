import os
import shutil
import stat
import unicodedata
import zipfile
from collections import deque
from pathlib import Path

from .errors import ZiprError
from .log import log

# Deflate cannot exceed a ~1032:1 ratio, so an archive expanding further was
# crafted (e.g. overlapping entries) rather than made of compressible data.
MAX_COMPRESSION_RATIO = 1100

# Same order of magnitude as the kernel's own limit (40 on Linux, 32 on macOS).
MAX_LINK_HOPS = 40


def extract_archive(
    archive_path: str, destination: str, max_size: int | None = None
) -> None:
    """Extract archive_path into destination after validating every member."""
    destination_path = Path(destination).resolve()

    with zipfile.ZipFile(archive_path) as zipf:
        members = zipf.infolist()
        _check_members(zipf, members, destination_path)
        _check_size(members, archive_path, destination_path, max_size)

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
        _canonical_name(member.filename): member
        for member in members
        if _is_symlink(member)
    }

    nested_members = [
        member.filename
        for member in members
        if any(
            "/".join(parent) in links
            for parent in _prefixes(_canonical_name(member.filename))
        )
    ]
    if nested_members:
        raise ZiprError(
            f"Member(s) stored below a link in ZIP archive: {', '.join(nested_members)}"
        )

    targets = {name: _read_link_target(zipf, member) for name, member in links.items()}
    directories = _archive_directories(members, links)
    folded = {_fold(name) for name in targets}, {_fold(name) for name in directories}
    unsafe_links = [
        f"{name} -> {target}"
        for name, target in targets.items()
        if not _is_safe_link_target(
            name, target, targets, directories, folded, destination
        )
    ]
    if unsafe_links:
        raise ZiprError(f"Unsafe link(s) in ZIP archive: {', '.join(unsafe_links)}")


def _check_size(
    members: list[zipfile.ZipInfo],
    archive_path: str,
    destination: Path,
    max_size: int | None,
) -> None:
    """
    Refuse zip bombs based on the sizes declared in the central directory.

    Declared sizes can be trusted as an upper bound: zipfile stops reading a
    member once its declared size has been produced.
    """
    total_size = sum(member.file_size for member in members)
    archive_size = max(os.path.getsize(archive_path), 1)

    if max_size is not None and total_size > max_size:
        raise ZiprError(
            f"Archive expands to {format_size(total_size)}, "
            f"above --max-size {format_size(max_size)}."
        )

    if total_size / archive_size > MAX_COMPRESSION_RATIO:
        raise ZiprError(
            f"Archive expands to {format_size(total_size)} from "
            f"{format_size(archive_size)}: this is not achievable with deflate, "
            "it looks like a zip bomb."
        )

    free_space = shutil.disk_usage(_existing_ancestor(destination)).free
    if total_size > free_space:
        raise ZiprError(
            f"Archive expands to {format_size(total_size)} but only "
            f"{format_size(free_space)} is free on the destination disk."
        )


def _existing_ancestor(path: Path) -> Path:
    while not path.exists():
        path = path.parent
    return path


def format_size(size: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            break
        size /= 1024
    return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"


def _is_within(path: Path, directory: Path) -> bool:
    resolved = path.resolve()
    return resolved == directory or directory in resolved.parents


def _is_symlink(member: zipfile.ZipInfo) -> bool:
    return member.create_system == 3 and stat.S_ISLNK(member.external_attr >> 16)


def _read_link_target(zipf: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    return zipf.read(member).decode("utf-8")


def _canonical_name(filename: str) -> str:
    """Where zipfile.extract actually puts a member: it drops '', '.' and '..'."""
    return "/".join(part for part in filename.split("/") if part not in ("", ".", ".."))


def _prefixes(name: str) -> list[tuple[str, ...]]:
    parts = tuple(name.split("/"))
    return [parts[:i] for i in range(1, len(parts))]


def _fold(name: str) -> str:
    """Names that may designate the same file on a case-insensitive filesystem."""
    return unicodedata.normalize("NFC", name).casefold()


def _archive_directories(
    members: list[zipfile.ZipInfo], links: dict[str, zipfile.ZipInfo]
) -> set[str]:
    directories = set()
    for member in members:
        name = _canonical_name(member.filename)
        directories.update("/".join(parent) for parent in _prefixes(name))
        if member.is_dir():
            directories.add(name)
    return directories - links.keys()


def _is_safe_link_target(
    name: str,
    target: str,
    links: dict[str, str],
    directories: set[str],
    folded: tuple[set[str], set[str]],
    destination: Path,
) -> bool:
    """
    Resolve the link the way the kernel will once everything is extracted,
    following the archive's own links and those already in the destination,
    and require every step to stay inside the destination.

    Checking the target as text is not enough: with 'b -> .', the target
    'b/b/../../etc' looks harmless but climbs two levels above the link.
    """
    if not target or os.path.isabs(target):
        return False

    folded_links, folded_directories = folded

    # The link's own directory is resolved too, since it may sit below a link
    # already present in the destination.
    pending = deque(name.split("/")[:-1] + target.split("/"))
    current: list[str] = []
    hops = 0

    while pending:
        part = pending.popleft()
        if part in ("", "."):
            continue

        if part == "..":
            # '..' is only predictable from a real directory: from a path that
            # does not exist yet, a later extraction could turn it into a link.
            if not current or not _is_real_directory(
                current, directories, folded_directories, destination
            ):
                return False
            current.pop()
            continue

        candidate = "/".join([*current, part])
        if candidate in links:
            link_target = links[candidate]
        elif _fold(candidate) in folded_links:
            # Another spelling of an archive link: the filesystem may or may not
            # treat it as the same file, so its resolution is unknown.
            return False
        elif (destination / candidate).is_symlink():
            link_target = os.readlink(destination / candidate)
        else:
            current.append(part)
            continue

        hops += 1
        if hops > MAX_LINK_HOPS:
            return False
        if os.path.isabs(link_target):
            try:
                relative = Path(link_target).relative_to(destination)
            except ValueError:
                return False
            current = []
            link_target = relative.as_posix()
        pending.extendleft(reversed(link_target.split("/")))

    return True


def _is_real_directory(
    parts: list[str],
    directories: set[str],
    folded_directories: set[str],
    destination: Path,
) -> bool:
    name = "/".join(parts)
    if name in directories:
        return True
    if _fold(name) in folded_directories:
        return False
    path = destination / name
    return path.is_dir() and not path.is_symlink()


def _create_symlink(
    zipf: zipfile.ZipFile, member: zipfile.ZipInfo, destination: Path
) -> None:
    path = destination / _canonical_name(member.filename)
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
