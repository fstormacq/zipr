#!/usr/bin/env sh

set -e

echo "Initializing project environment, using uv..."

uv sync
uv run pre-commit install

echo "Project environment initialized. Pre-commit is now installed."