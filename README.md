# zipr

A lightweight ZIP helper that uses Python's `zipfile` with ISA-L compression support.

## Installation

From the project root:

```sh
uv sync
```

Install the CLI entry points in your environment if needed:

```sh
uv tool install .
```

## Usage

### `zipr`

```sh
uv run zipr INPUT [--output OUTPUT] [--level 0-3] [--threads N] [--force] [--verbose] [--debug]
```

`INPUT` can be a file or a directory.

If `--output` is not provided:
- a file input `photo.jpg` produces `photo.zip`
- a directory input `documents` produces `documents.zip` next to it (also for `.`)

Examples:

```sh
uv run zipr ./documents
uv run zipr ./documents --output ./archives/documents.zip
uv run zipr ./photo.jpg -o ./archives/photo.zip
uv run zipr ./documents --level 0 --verbose
```

Available options:

```text
--output, -o    Output ZIP file
--level, -l     ISA-L compression level, 0 (fastest) to 3 (smallest), default 2
--threads, -t   Thread count (minimum 1, maximum and default: CPU count)
--force, -f     Overwrite the output without asking
--verbose       Enable informational logs
--debug         Enable debug logs
```

Behavior notes:
- Entries are added in sorted order, so the same input always gives the same archive.
- Empty directories are kept; symbolic links are stored as links, not followed
  (a link given directly as `INPUT` is followed).
- The archive is written to a temporary file and moved into place at the end:
  an error or Ctrl-C never leaves a corrupted archive or destroys the previous one.
- If the output lives inside the input directory, it is not added to itself.
- Missing parent directories for the output archive are created automatically.
- If the output already exists, the command asks before overwriting it, or fails
  when there is no terminal to ask; use `--force` in scripts.

### `unzipr`

```sh
uv run unzipr ARCHIVE.zip [--output DIRECTORY] [--max-size SIZE] [--threads N] [--force] [--verbose] [--debug]
```

`ARCHIVE.zip` must be a valid ZIP archive. If `--output` is omitted, the
destination is the archive path without its extension.

Examples:

```sh
uv run unzipr ./archive.zip
uv run unzipr ./archive.zip --output ./extracted --max-size 2G
```

Safety notes:
- The whole archive is validated before anything is written. It is refused if a
  member or a link would escape the destination, or if a member is stored below a link.
- Zip bombs are refused: the declared size must fit in `--max-size` (if given) and
  in the free disk space, and cannot exceed the 1100:1 ratio deflate is capable of.
- File permissions (rwx) are restored; setuid, setgid and sticky bits are dropped.
- Existing output directories are not cleared; files with the same name are overwritten.

All logs go to stderr. Colors are disabled when stderr is not a terminal or
`NO_COLOR` is set.

## Development

Install the local Git hook:

```sh
./init.sh
```

Run the checks:

```sh
uv run pytest
uvx ruff check --fix
uvx ruff format 
uv run pre-commit run --all-files
```

## Notes

Requires Python 3.11 or later.

The current implementation is single-threaded: `--threads` is accepted but has no effect yet. Parallel, chunked compression is the next step.
