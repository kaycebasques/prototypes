#!/usr/bin/env bash

BUILDER="html"
SRC="."
OUT="_build/html"
uv run sphinx-build --fresh-env --write-all --fail-on-warning --builder $BUILDER $SRC $OUT
