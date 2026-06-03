#!/bin/bash
set -e

# Path to this script's directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

BUILD_DIR="${DIR}/build"

# Configure if not already configured
if [ ! -d "${BUILD_DIR}" ]; then
  cmake -B "${BUILD_DIR}" -S "${DIR}" -G Ninja
fi

# Construct PYTHONPATH for the build process
PYTHON_PACKAGES_DIR="${BUILD_DIR}/python_packages"
PIGWEED_DIR="${BUILD_DIR}/_deps/pigweed-src"

export PYTHONPATH="${PYTHON_PACKAGES_DIR}:${PIGWEED_DIR}/pw_protobuf/py:${PIGWEED_DIR}/pw_status/py:${PIGWEED_DIR}/pw_protobuf_compiler/py:${PIGWEED_DIR}/pw_rpc/py:${PIGWEED_DIR}/pw_stream/py:${PIGWEED_DIR}/pw_log/py:${PIGWEED_DIR}/pw_cli/py:${PYTHONPATH}"

# Run the build
cmake --build "${BUILD_DIR}" --target rpc_demo
