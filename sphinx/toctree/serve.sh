#!/usr/bin/env bash

./build.sh
OUT="_build/html"
python3 -m http.server -d $OUT 8008
