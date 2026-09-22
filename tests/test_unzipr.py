import sys
import zipfile

import pytest

from src.unzipr import main


@pytest.mark.integration
def test_cli_unzips_zip_file(monkeypatch, tmp_path):
    input_file = tmp_path / "archive.zip"
    with zipfile.ZipFile(input_file, "w") as archive:
        archive.writestr("nested/file.txt", "test content")

    output_directory = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["unzipr", str(input_file), "--output", str(output_directory)],
    )

    main()

    extracted_file = output_directory / "nested" / "file.txt"
    assert extracted_file.read_text() == "test content"
