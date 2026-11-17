import os
import stat
import zipfile

import pytest

from zipr.archive import create_archive
from zipr.errors import ZiprError
from zipr.extract import extract_archive


@pytest.mark.integration
def test_extracts_archive(tmp_path):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("nested/file.txt", "test content")
    output_directory = tmp_path / "output"

    extract_archive(str(archive), str(output_directory))

    assert (output_directory / "nested" / "file.txt").read_text() == "test content"


@pytest.mark.integration
@pytest.mark.parametrize("unsafe_name", ["../evil.txt", "/tmp/evil.txt"])
def test_rejects_unsafe_archive_before_extracting(tmp_path, unsafe_name):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("safe.txt", "safe content")
        zipf.writestr(unsafe_name, "evil content")
    output_directory = tmp_path / "output"

    with pytest.raises(ZiprError, match="Unsafe path"):
        extract_archive(str(archive), str(output_directory))

    assert not (output_directory / "safe.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


def make_link(archive, name, target):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    archive.writestr(info, target)


@pytest.mark.integration
def test_round_trip_keeps_links_modes_and_empty_directories(tmp_path):
    input_directory = tmp_path / "input"
    (input_directory / "empty").mkdir(parents=True)
    (input_directory / "lib").mkdir()
    script = input_directory / "run.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    (input_directory / "lib" / "libfoo.so.1").write_text("binary")
    (input_directory / "lib" / "libfoo.so").symlink_to("libfoo.so.1")
    (input_directory / "lib_link").symlink_to("lib")
    archive = tmp_path / "archive.zip"
    output_directory = tmp_path / "output"

    create_archive(str(input_directory), str(archive))
    extract_archive(str(archive), str(output_directory))

    assert (output_directory / "empty").is_dir()
    assert (output_directory / "run.sh").stat().st_mode & 0o777 == 0o755
    assert os.readlink(output_directory / "lib" / "libfoo.so") == "libfoo.so.1"
    assert (output_directory / "lib" / "libfoo.so").read_text() == "binary"
    assert os.readlink(output_directory / "lib_link") == "lib"


@pytest.mark.integration
def test_drops_setuid_bit(tmp_path):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        info = zipfile.ZipInfo("tool")
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | stat.S_ISUID | 0o755) << 16
        zipf.writestr(info, "binary")
    output_directory = tmp_path / "output"

    extract_archive(str(archive), str(output_directory))

    assert (output_directory / "tool").stat().st_mode & 0o7777 == 0o755


@pytest.mark.integration
@pytest.mark.parametrize("target", ["/etc/passwd", "../outside", "a/../../outside"])
def test_rejects_link_escaping_destination(tmp_path, target):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("safe.txt", "safe content")
        make_link(zipf, "link", target)
    output_directory = tmp_path / "output"

    with pytest.raises(ZiprError, match="Unsafe link"):
        extract_archive(str(archive), str(output_directory))

    assert not (output_directory / "safe.txt").exists()


@pytest.mark.integration
def test_rejects_member_stored_below_a_link(tmp_path):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        make_link(zipf, "link", "sub")
        zipf.writestr("link/file.txt", "written through the link")
    output_directory = tmp_path / "output"

    with pytest.raises(ZiprError, match="below a link"):
        extract_archive(str(archive), str(output_directory))
