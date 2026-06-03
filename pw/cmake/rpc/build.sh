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
GENERATED_PYTHON_DIR="${BUILD_DIR}/generated_python/python"
PIGWEED_DIR="/usr/local/google/home/kayce/wip/pigweed"

export PYTHONPATH="${GENERATED_PYTHON_DIR}:${PIGWEED_DIR}/pw_protobuf/py:${PIGWEED_DIR}/pw_status/py:${PIGWEED_DIR}/pw_protobuf_compiler/py:${PIGWEED_DIR}/pw_rpc/py:${PIGWEED_DIR}/pw_stream/py:${PIGWEED_DIR}/pw_log/py:${PIGWEED_DIR}/pw_cli/py:${PYTHONPATH}"

# Run the build
cmake --build "${BUILD_DIR}" --target rpc_demo
