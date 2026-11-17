import os
import shutil
import stat
import zipfile

import pytest

from zipr.archive import create_archive
from zipr.errors import ZiprError
from zipr.extract import extract_archive, format_size


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


@pytest.mark.integration
def test_accepts_highly_compressible_data(tmp_path):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        zipf.writestr("zeros.bin", bytes(10 * 1024**2))

    extract_archive(str(archive), str(tmp_path / "output"))

    assert (tmp_path / "output" / "zeros.bin").stat().st_size == 10 * 1024**2


@pytest.mark.integration
def test_rejects_impossible_compression_ratio(tmp_path):
    # Many entries sharing the same compressed data, like the classic
    # overlapping zip bomb, expand far beyond what deflate can achieve.
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("zeros.bin", bytes(1024**2))
    with zipfile.ZipFile(archive, "a") as zipf:
        original = zipf.getinfo("zeros.bin")
        for index in range(2000):
            clone = zipfile.ZipInfo(f"clone-{index}.bin", original.date_time)
            for attribute in ("compress_type", "CRC", "compress_size", "file_size"):
                setattr(clone, attribute, getattr(original, attribute))
            clone.header_offset = original.header_offset
            zipf.filelist.append(clone)
            zipf.NameToInfo[clone.filename] = clone
        zipf._didModify = True

    with pytest.raises(ZiprError, match="zip bomb"):
        extract_archive(str(archive), str(tmp_path / "output"))
    assert not (tmp_path / "output").exists()


@pytest.mark.integration
def test_rejects_archive_larger_than_free_space(tmp_path, monkeypatch):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("file.txt", "x" * 2048)
    monkeypatch.setattr(
        "shutil.disk_usage", lambda _: shutil._ntuple_diskusage(0, 0, 1024)
    )

    with pytest.raises(ZiprError, match="free on the destination disk"):
        extract_archive(str(archive), str(tmp_path / "output"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("size", "expected"),
    [(0, "0 B"), (1023, "1023 B"), (1536, "1.5 KiB"), (5 * 1024**3, "5.0 GiB")],
)
def test_format_size(size, expected):
    assert format_size(size) == expected
