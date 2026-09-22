import argparse
import zipfile

import pytest

from src.utils.arg_parser import check_cli_args, parse_unzip_args, parse_zip_args


def make_args(input_path, output=None, threads=4):
    return argparse.Namespace(
        input=str(input_path),
        output=str(output) if output is not None else None,
        threads=threads,
        verbose=False,
        debug=False,
    )


@pytest.mark.unit
def test_parse_zip_args_with_missing_input(monkeypatch):
    monkeypatch.setattr("sys.argv", ["zipr", "missing.txt"])

    with pytest.raises(SystemExit):
        parse_zip_args()


@pytest.mark.unit
def test_parse_zip_args_with_verbose(monkeypatch, tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    monkeypatch.setattr("sys.argv", ["zipr", str(input_file), "--verbose"])
    args = parse_zip_args()
    assert args.input == str(input_file)
    assert args.verbose
    assert not args.debug


@pytest.mark.unit
def test_parse_zip_args_with_debug(monkeypatch, tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    monkeypatch.setattr("sys.argv", ["zipr", str(input_file), "--debug"])
    args = parse_zip_args()
    assert args.input == str(input_file)
    assert not args.verbose
    assert args.debug


@pytest.mark.unit
def test_parse_zip_args_with_all_flags(monkeypatch, tmp_path):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    monkeypatch.setattr(
        "sys.argv",
        ["zipr", str(input_file), "--verbose", "--debug"],
    )
    args = parse_zip_args()
    assert args.input == str(input_file)
    assert args.verbose
    assert args.debug


@pytest.mark.unit
def test_check_cli_args_rejects_missing_input(tmp_path):
    args = make_args(tmp_path / "missing.txt")

    with pytest.raises(SystemExit):
        check_cli_args(args)


@pytest.mark.unit
def test_check_cli_args_accepts_directory_for_zip_cli(tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    args = make_args(input_directory)

    check_cli_args(args)

    assert args.output == f"{input_directory}.zip"


@pytest.mark.unit
def test_check_cli_args_allows_existing_output_directory(tmp_path, monkeypatch):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    output_directory = tmp_path / "existing-output"
    output_directory.mkdir()
    args = make_args(input_file, output_directory / "archive.zip")
    monkeypatch.setattr(
        "builtins.input",
        lambda _: pytest.fail("Should not ask to overwrite the output directory"),
    )

    check_cli_args(args)

    assert args.output == str(output_directory / "archive.zip")


@pytest.mark.unit
def test_parse_unzip_args_rejects_directory(monkeypatch, tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    monkeypatch.setattr("sys.argv", ["unzipr", str(input_directory)])

    with pytest.raises(SystemExit):
        parse_unzip_args()


@pytest.mark.unit
def test_parse_unzip_args_accepts_zip_file(monkeypatch, tmp_path):
    input_file = tmp_path / "archive.zip"
    with zipfile.ZipFile(input_file, "w"):
        pass

    monkeypatch.setattr("sys.argv", ["unzipr", str(input_file)])

    args = parse_unzip_args()

    assert args.input == str(input_file)
    assert args.output == f"{tmp_path / 'archive'}"


@pytest.mark.unit
def test_check_cli_args_creates_default_output_for_directory(tmp_path):
    input_directory = tmp_path / "input"
    input_directory.mkdir()
    args = make_args(input_directory)

    check_cli_args(args)

    assert args.output == f"{input_directory}.zip"


@pytest.mark.unit
def test_check_cli_args_clamps_invalid_thread_count(tmp_path, monkeypatch):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    args = make_args(input_file, tmp_path / "output.zip", threads=0)

    check_cli_args(args)

    assert args.threads == 1


@pytest.mark.unit
def test_check_cli_args_clamps_threads_to_cpu_count(tmp_path, monkeypatch):
    input_file = tmp_path / "input.txt"
    input_file.touch()
    args = make_args(input_file, tmp_path / "output.zip", threads=16)
    monkeypatch.setattr("src.utils.arg_parser.os.cpu_count", lambda: 8)

    check_cli_args(args)

    assert args.threads == 8
