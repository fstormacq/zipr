# zipr
`zip`, but it actually uses all your cores. (NOT SUPPORTED FOR THE MOMENT, ONLY SINGLE-THREADED MODE IS AVAILABLE)

## Usage

Run zipr with an input file or directory:

```sh
uv run zipr INPUT
```

The output path defaults to `INPUT.zip`. You can specify another ZIP file with
`--output` or `-o`:

```sh
uv run zipr ./documents -o ./archives/documents.zip
uv run zipr ./photo.jpg -o ./archives/photo.zip
```

Available options:

```text
--output, -o    Output ZIP file
--threads, -t   Number of threads to use (default: 4)
--verbose       Enable informational logs
--debug         Enable debug logs
```

If the output file already exists, zipr asks for confirmation before replacing
it. Missing parent directories for the output file are created automatically.

## Tests

Run the test suite with:

```sh
uv run pytest
```

## Development

To install the pre-commit hook, run:

```sh
./init.sh
```

### Pre-commit

Check the code style with:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pre-commit run --all-files
```

### Test execution

Run the tests with:

```sh
uv run pytest
```