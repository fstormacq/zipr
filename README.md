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

### Benchmark: single thread (`-t 1`)

Same input directory, output validated with `diff -r` (identical content).

| Tool | Level | Wall time | User CPU | Archive size | Size vs `zip -6` | Speedup vs `zip -6` |
|---|---|---|---|---|---|---|
| `zip` (zlib) | 6 (default) | 55.51 s | 52.15 s | 1.42 GB | baseline | 1.0x |
| `zipr` (ISA-L) | 3 (`ISAL_BEST_COMPRESSION`) | 14.07 s | 11.03 s | 1.48 GB | +4.3% | 3.9x |
| `zipr` (ISA-L) | 2 (`ISAL_DEFAULT_COMPRESSION`) | 14.18 s | 10.98 s | 1.49 GB | +5.1% | 3.9x |
| `zipr` (ISA-L) | 0 (`ISAL_BEST_SPEED`) | 10.97 s | 6.33 s | 1.83 GB | +28.9% | 5.1x |

**Comments**

- ISA-L level 3 is the best trade-off: about 3.9x faster than `zip -6` for a 4.3% larger archive. Level 2 gives the same speed with a slightly larger file, so it offers no advantage here.
- Level 0 saves about 3 s over level 3 but adds about 350 MB (+24% vs level 3), which is not worth it for a folder where size matters.
- ISA-L levels (0-3) are not equivalent to zlib levels (1-9), so compare measured size and time, not level numbers.
- Reading the whole source with `tar cf /dev/null` takes 4.65 s (warm cache), so the I/O floor is well below the current runtime. There is CPU headroom for multi-threaded compression.