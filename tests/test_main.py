import sys
import zipfile

import pytest

from src.main import main


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
