#!/usr/bin/env bash

BUILD_DIR="_build"

if [ -d "$BUILD_DIR" ]; then
  rm -rf "$BUILD_DIR"
fi

BUILDER="html"
SRC="."
OUT="$BUILD_DIR/html"
uv run sphinx-build --fresh-env --write-all --fail-on-warning --builder $BUILDER $SRC $OUT
