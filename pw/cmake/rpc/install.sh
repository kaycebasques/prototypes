#!/bin/bash
set -e

sudo apt-get update
sudo apt-get install -y \
  build-essential \
  cmake \
  ninja-build \
  protobuf-compiler \
  python3 \
  python3-protobuf \
  python3-serial
