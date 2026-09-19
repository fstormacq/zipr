import pytest

from src.utils.arg_parser import parse_args


@pytest.mark.unit
def test_parse_args_with_empty_input(monkeypatch):
    monkeypatch.setattr("sys.argv", ["zipr", ""])
    args = parse_args()
    assert args.input == ""
    assert not args.verbose
    assert not args.debug


@pytest.mark.unit
def test_parse_args_with_verbose(monkeypatch):
    monkeypatch.setattr("sys.argv", ["zipr", "input.txt", "--verbose"])
    args = parse_args()
    assert args.input == "input.txt"
    assert args.verbose
    assert not args.debug


@pytest.mark.unit
def test_parse_args_with_debug(monkeypatch):
    monkeypatch.setattr("sys.argv", ["zipr", "input.txt", "--debug"])
    args = parse_args()
    assert args.input == "input.txt"
    assert not args.verbose
    assert args.debug


@pytest.mark.unit
def test_parse_args_with_all_flags(monkeypatch):
    monkeypatch.setattr("sys.argv", ["zipr", "input.txt", "--verbose", "--debug"])
    args = parse_args()
    assert args.input == "input.txt"
    assert args.verbose
    assert args.debug
