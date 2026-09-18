# zipr
`zip`, but it actually uses all your cores.

## Development

In order to harmonize the code style, you can run the following commands to add a pre-commit hook and check the code style:

```sh
./init.sh
```

Then, you can run the following commands to check the code style:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pre-commit run --all-files
```