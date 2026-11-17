import contextlib
import os
import stat
import tempfile
import time
import zipfile
from collections.abc import Generator, Iterator

from isal import isal_zlib

from .log import log

COMPRESSION_LEVELS = range(
    isal_zlib.ISAL_BEST_SPEED, isal_zlib.ISAL_BEST_COMPRESSION + 1
)
# Level 3 is ~1.7x slower than level 2 for about 1% smaller archives.
DEFAULT_COMPRESSION_LEVEL = isal_zlib.ISAL_DEFAULT_COMPRESSION


def create_archive(
    input_path: str, output_path: str, level: int = DEFAULT_COMPRESSION_LEVEL
) -> None:
    """Zip a file or a directory, atomically replacing output_path."""
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    tmp_path = _create_temp_file(output_path)
    excluded_paths = {os.path.realpath(output_path), os.path.realpath(tmp_path)}

    try:
        with (
            _isal_backend(),
            zipfile.ZipFile(
                tmp_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=level,
            ) as zipf,
        ):
            for path, archive_name in _iter_entries(input_path, excluded_paths):
                log.debug("Adding %s", archive_name)
                # A link named explicitly on the command line is followed.
                _add_entry(zipf, path, archive_name, follow_link=path == input_path)
        os.replace(tmp_path, output_path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp_path)
        raise


@contextlib.contextmanager
def _isal_backend() -> Generator[None]:
    """
    Route zipfile's deflate through ISA-L for the duration of the block.

    zipfile has no hook for a custom compressor, so this swaps its module-level
    zlib reference and restores it afterwards.
    """
    previous = zipfile.zlib
    zipfile.zlib = isal_zlib
    try:
        yield
    finally:
        zipfile.zlib = previous


def _create_temp_file(output_path: str) -> str:
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


def _iter_entries(
    input_path: str, excluded_paths: set[str]
) -> Iterator[tuple[str, str]]:
    """
    Yield (path, archive name) pairs for everything under input_path, sorted
    so the same input always produces the same archive.

    Directories are yielded too, so empty ones survive. Symbolic links are
    yielded but never followed.
    """
    if os.path.isfile(input_path):
        yield input_path, os.path.basename(input_path)
        return

    for root, dirs, files in os.walk(input_path):
        log.debug("Walking through directory: %s", root)
        dirs.sort()
        if root != input_path:
            yield root, os.path.relpath(root, input_path)

        linked_dirs = [d for d in dirs if os.path.islink(os.path.join(root, d))]
        for name in sorted(files + linked_dirs):
            path = os.path.join(root, name)
            if not os.path.islink(path) and os.path.realpath(path) in excluded_paths:
                log.debug("Skipping output archive: %s", path)
                continue
            yield path, os.path.relpath(path, input_path)


def _add_entry(
    zipf: zipfile.ZipFile, path: str, archive_name: str, follow_link: bool
) -> None:
    if follow_link or not os.path.islink(path):
        zipf.write(path, archive_name)
        return

    # Store the link itself, like `zip --symlinks`: the target path is the
    # member's content and the mode marks it as a link.
    st = os.lstat(path)
    date_time = max(time.localtime(st.st_mtime)[:6], (1980, 1, 1, 0, 0, 0))
    zinfo = zipfile.ZipInfo(archive_name, date_time)
    zinfo.create_system = 3  # Unix, so external_attr holds st_mode
    zinfo.external_attr = (stat.S_IFLNK | 0o777) << 16
    zipf.writestr(zinfo, os.readlink(path), compress_type=zipfile.ZIP_STORED)
