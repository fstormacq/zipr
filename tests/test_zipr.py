import sys
import zipfile
import zlib

import pytest
from isal import isal_zlib

from zipr.zipr import main


@pytest.mark.integration
def test_cli_zips_directory(monkeypatch, tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    input_file = input_directory / "nested" / "file.txt"
    input_file.parent.mkdir()
    input_file.write_text("test content")

    output_file = tmp_path / "archive.zip"
    monkeypatch.setattr(
        sys,
        "argv",
        ["zipr", str(input_directory), "--output", str(output_file)],
    )

    main()

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["nested/file.txt"]
        assert archive.read("nested/file.txt") == b"test content"


@pytest.mark.integration
def test_cli_zips_file(monkeypatch, tmp_path):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")

    output_file = tmp_path / "archive.zip"
    monkeypatch.setattr(
        sys,
        "argv",
        ["zipr", str(input_file), "--output", str(output_file)],
    )

    main()

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["file.txt"]
        assert archive.read("file.txt") == b"test content"


@pytest.mark.integration
def test_cli_does_not_include_output_archive(monkeypatch, tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    (input_directory / "file.txt").write_text("test content")

    output_file = input_directory / "archive.zip"
    monkeypatch.setattr(
        sys,
        "argv",
        ["zipr", str(input_directory), "--output", str(output_file)],
    )

    main()

    with zipfile.ZipFile(output_file) as archive:
        assert archive.namelist() == ["file.txt"]
    assert sorted(p.name for p in input_directory.iterdir()) == [
        "archive.zip",
        "file.txt",
    ]


@pytest.mark.integration
def test_cli_uses_isal_regardless_of_thread_count(monkeypatch, tmp_path):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"
    monkeypatch.setattr("os.cpu_count", lambda: 4)
    monkeypatch.setattr(zipfile, "zlib", zlib)
    monkeypatch.setattr(
        sys,
        "argv",
        ["zipr", str(input_file), "--output", str(output_file), "--threads", "2"],
    )

    main()

    assert zipfile.zlib is isal_zlib
    with zipfile.ZipFile(output_file) as archive:
        assert archive.read("file.txt") == b"test content"


@pytest.mark.integration
def test_cli_keeps_existing_archive_on_failure(monkeypatch, tmp_path):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"
    output_file.write_bytes(b"previous archive")

    def fail(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        ["zipr", str(input_file), "--output", str(output_file), "--force"],
    )

    with pytest.raises(OSError):
        main()

    assert output_file.read_bytes() == b"previous archive"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["archive.zip", "file.txt"]
