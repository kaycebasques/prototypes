#!/bin/bash
set -e

# Path to this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

BUILD_DIR="${DIR}/build"

# Configure if not already configured
if [ ! -d "${BUILD_DIR}" ]; then
  cmake -B "${BUILD_DIR}" -S "${DIR}" -G Ninja
fi

# Run the build
cmake --build "${BUILD_DIR}" --target rpc_demo
