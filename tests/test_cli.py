import io
import zipfile

import pytest

from zipr.cli import (
    confirm_overwrite,
    default_unzip_output,
    default_zip_output,
    normalize_threads,
    parse_unzip_args,
    parse_zip_args,
    unzip_main,
    zip_main,
)
from zipr.errors import ZiprError


@pytest.fixture
def stdin(monkeypatch):
    """Replace stdin with a buffer whose TTY status can be chosen."""

    def make(content="", tty=True):
        buffer = io.StringIO(content)
        buffer.isatty = lambda: tty
        monkeypatch.setattr("sys.stdin", buffer)

    return make


# ── Argument parsing ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_parse_zip_args_flags():
    args = parse_zip_args(["input", "--verbose", "--debug", "-f", "-t", "2"])

    assert args.input == "input"
    assert args.verbose
    assert args.debug
    assert args.force
    assert args.threads == 2


@pytest.mark.unit
def test_parse_args_defaults_threads_to_cpu_count(monkeypatch):
    monkeypatch.setattr("os.cpu_count", lambda: 6)

    assert parse_zip_args(["input"]).threads == 6
    assert parse_unzip_args(["input.zip"]).threads == 6


@pytest.mark.unit
@pytest.mark.parametrize("threads", ["0", "-1", "two"])
def test_parse_args_rejects_invalid_thread_count(threads):
    with pytest.raises(SystemExit) as exc_info:
        parse_zip_args(["input", "--threads", threads])

    assert exc_info.value.code == 2


@pytest.mark.unit
def test_normalize_threads_clamps_to_cpu_count(monkeypatch):
    monkeypatch.setattr("os.cpu_count", lambda: 8)

    assert normalize_threads(16) == 8
    assert normalize_threads(4) == 4


# ── Default outputs ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_default_zip_output_for_directory(tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()

    assert default_zip_output(str(input_directory)) == f"{input_directory}.zip"


@pytest.mark.unit
def test_default_zip_output_for_file(tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.touch()

    assert default_zip_output(str(input_file)) == str(tmp_path / "input.zip")


@pytest.mark.unit
@pytest.mark.parametrize("current_directory", [".", "./"])
def test_default_zip_output_for_current_directory(
    tmp_path, monkeypatch, current_directory
):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    monkeypatch.chdir(input_directory)

    assert default_zip_output(current_directory) == str(tmp_path / "input.zip")


@pytest.mark.unit
def test_default_zip_output_for_root_requires_explicit_output():
    with pytest.raises(ZiprError):
        default_zip_output("/")


@pytest.mark.unit
def test_default_unzip_output_strips_extension():
    assert default_unzip_output("dir/archive.zip") == "dir/archive"


# ── Overwrite confirmation ───────────────────────────────────────────────────


@pytest.mark.unit
def test_confirm_overwrite_when_output_is_missing(tmp_path, stdin):
    stdin(tty=False)

    assert confirm_overwrite(str(tmp_path / "missing.zip"), force=False)


@pytest.mark.unit
def test_confirm_overwrite_refuses_without_tty(tmp_path, stdin):
    output_file = tmp_path / "output.zip"
    output_file.touch()
    stdin(tty=False)

    with pytest.raises(ZiprError, match="--force"):
        confirm_overwrite(str(output_file), force=False)


@pytest.mark.unit
def test_confirm_overwrite_with_force(tmp_path, stdin):
    output_file = tmp_path / "output.zip"
    output_file.touch()
    stdin(tty=False)

    assert confirm_overwrite(str(output_file), force=True)


@pytest.mark.unit
@pytest.mark.parametrize(("answer", "expected"), [("y\n", True), ("n\n", False)])
def test_confirm_overwrite_asks_the_user(tmp_path, stdin, answer, expected):
    output_file = tmp_path / "output.zip"
    output_file.touch()
    stdin(answer)

    assert confirm_overwrite(str(output_file), force=False) is expected


@pytest.mark.unit
def test_confirm_overwrite_cancels_on_eof(tmp_path, stdin):
    output_file = tmp_path / "output.zip"
    output_file.touch()
    stdin("")

    assert not confirm_overwrite(str(output_file), force=False)


# ── End to end ───────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_zip_main_reports_missing_input(tmp_path, capsys):
    assert zip_main([str(tmp_path / "missing.txt")]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "does not exist" in captured.err


@pytest.mark.integration
def test_unzip_main_rejects_directory(tmp_path, capsys):
    assert unzip_main([str(tmp_path)]) == 1
    assert "not a valid ZIP archive" in capsys.readouterr().err


@pytest.mark.integration
def test_zip_main_keeps_stdout_clean(tmp_path, capsys):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"

    assert zip_main([str(input_file), "-o", str(output_file), "--debug"]) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Adding file.txt" in captured.err


@pytest.mark.integration
def test_zip_main_cancelled_by_user(tmp_path, stdin):
    input_file = tmp_path / "file.txt"
    input_file.write_text("test content")
    output_file = tmp_path / "archive.zip"
    output_file.write_bytes(b"previous archive")
    stdin("n\n")

    assert zip_main([str(input_file), "-o", str(output_file)]) == 0
    assert output_file.read_bytes() == b"previous archive"


@pytest.mark.integration
def test_round_trip(tmp_path):
    input_directory = tmp_path / "input"
    (input_directory / "nested").mkdir(parents=True)
    (input_directory / "nested" / "file.txt").write_text("test content")
    (input_directory / "top.bin").write_bytes(bytes(range(256)) * 100)
    archive = tmp_path / "archive.zip"
    output_directory = tmp_path / "output"

    assert zip_main([str(input_directory), "-o", str(archive)]) == 0
    assert zipfile.is_zipfile(archive)
    assert unzip_main([str(archive), "-o", str(output_directory)]) == 0

    assert (output_directory / "nested" / "file.txt").read_text() == "test content"
    assert (output_directory / "top.bin").read_bytes() == bytes(range(256)) * 100


@pytest.mark.integration
@pytest.mark.parametrize(("flag", "logged"), [([], False), (["--debug"], True)])
def test_unzip_main_logs_members_only_in_debug(tmp_path, capsys, flag, logged):
    archive = tmp_path / "archive.zip"
    with zipfile.ZipFile(archive, "w") as zipf:
        zipf.writestr("file.txt", "test content")

    assert unzip_main([str(archive), "-o", str(tmp_path / "out"), *flag]) == 0
    assert ("Extracting file.txt" in capsys.readouterr().err) is logged
