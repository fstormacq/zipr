import zipfile

import pytest

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
