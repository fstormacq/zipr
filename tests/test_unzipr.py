import sys
import zipfile

import pytest

from zipr.unzipr import main, safe_extract_all


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


@pytest.mark.integration
def test_cli_rejects_unsafe_archive_before_extracting(monkeypatch, tmp_path):
    input_file = tmp_path / "archive.zip"
    with zipfile.ZipFile(input_file, "w") as archive:
        archive.writestr("safe.txt", "safe content")
        archive.writestr("../evil.txt", "evil content")

    output_directory = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        ["unzipr", str(input_file), "--output", str(output_directory)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert not (output_directory / "safe.txt").exists()
    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.unit
def test_safe_extract_all_only_logs_members_in_debug(capsys, tmp_path):
    input_file = tmp_path / "archive.zip"
    with zipfile.ZipFile(input_file, "w") as archive:
        archive.writestr("file.txt", "test content")

    with zipfile.ZipFile(input_file) as archive:
        safe_extract_all(archive, str(tmp_path / "quiet"), debug=False)
    assert capsys.readouterr().out == ""

    with zipfile.ZipFile(input_file) as archive:
        safe_extract_all(archive, str(tmp_path / "loud"), debug=True)
    assert "Extracting file.txt" in capsys.readouterr().out
