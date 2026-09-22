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
uv run zipr INPUT [--output OUTPUT] [--threads N] [--verbose] [--debug]
```

`INPUT` can be a file or a directory.

If `--output` is not provided:
- a file input produces `INPUT.zip`
- a directory input produces `DIRECTORY.zip`

Examples:

```sh
uv run zipr ./documents
uv run zipr ./documents --output ./archives/documents.zip
uv run zipr ./photo.jpg -o ./archives/photo.zip
uv run zipr ./documents --threads 2 --verbose
```

Available options:

```text
--output, -o    Output ZIP file or archive path
--threads, -t   Thread count for the CLI (minimum 1, maximum CPU count)
--verbose       Enable informational logs
--debug         Enable debug logs
```

Behavior notes:
- Missing parent directories for the output archive are created automatically.
- If the archive already exists, the command prompts before overwriting it.
- For archive creation, the source must exist and be a file or directory.

### `unzipr`

```sh
uv run unzipr ARCHIVE.zip [--output DIRECTORY] [--threads N] [--verbose] [--debug]
```

`ARCHIVE.zip` must be a valid ZIP archive.

Examples:

```sh
uv run unzipr ./archive.zip
uv run unzipr ./archive.zip --output ./extracted
```

If `--output` is omitted, the destination is derived from the archive name.

Safety notes:
- Extraction rejects entries that would escape the chosen destination directory.
- Existing output directories are not cleared automatically.

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

The project currently focuses on a simple, robust ZIP workflow rather than a fully parallel implementation. A multi-threaded approach is planned for future releases, but the current implementation is single-threaded.