import zipfile
import zlib

import pytest
from isal import isal_zlib

from zipr.archive import create_archive


@pytest.mark.integration
def test_zips_directory(tmp_path):
    input_directory = tmp_path / "input"
    input_file = input_directory / "nested" / "file.txt"
    input_file.parent.mkdir(parents=True)
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"

    create_archive(str(input_directory), str(output_file))

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["nested/file.txt"]
        assert archive.read("nested/file.txt") == b"test content"


@pytest.mark.integration
def test_zips_file(tmp_path):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"

    create_archive(str(input_file), str(output_file))

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["file.txt"]
        assert archive.read("file.txt") == b"test content"


@pytest.mark.integration
def test_creates_missing_output_directories(tmp_path):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "a" / "b" / "archive.zip"

    create_archive(str(input_file), str(output_file))

    assert zipfile.is_zipfile(output_file)


@pytest.mark.integration
def test_does_not_include_output_archive(tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    (input_directory / "file.txt").write_text("test content")
    output_file = input_directory / "archive.zip"

    create_archive(str(input_directory), str(output_file))

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["file.txt"]
    assert sorted(p.name for p in input_directory.iterdir()) == [
        "archive.zip",
        "file.txt",
    ]


@pytest.mark.integration
def test_compresses_with_isal_without_leaking_the_patch(tmp_path, monkeypatch):
    calls = []
    original = isal_zlib.compressobj

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(isal_zlib, "compressobj", spy)
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")

    create_archive(str(input_file), str(tmp_path / "archive.zip"))

    assert calls
    assert zipfile.zlib is zlib


@pytest.mark.integration
def test_keeps_existing_archive_on_failure(tmp_path, monkeypatch):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"
    output_file.write_bytes(b"previous archive")

    def fail(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", fail)

    with pytest.raises(OSError):
        create_archive(str(input_file), str(output_file))

    assert output_file.read_bytes() == b"previous archive"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["archive.zip", "file.txt"]


@pytest.mark.integration
def test_compression_level_is_forwarded_to_isal(tmp_path, monkeypatch):
    levels = []
    original = isal_zlib.compressobj

    def spy(level, *args, **kwargs):
        levels.append(level)
        return original(level, *args, **kwargs)

    monkeypatch.setattr(isal_zlib, "compressobj", spy)
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")

    create_archive(str(input_file), str(tmp_path / "default.zip"))
    create_archive(str(input_file), str(tmp_path / "fast.zip"), level=0)

    assert levels == [2, 0]
