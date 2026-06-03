# Prototype: RPC + CMake - bootstrap

A minimal application built with CMake that sets up a `pw_rpc` server
and uses Nanopb for protobuf codegen. The app and protobuf codegen builds
without a Pigweed bootstrap. I use a bootstrap to spin up `pw_console` and
verify that I can send an RPC to the app.

## Toolchain

On Debian-based systems, running `./install.sh` should get you
most or everything you need. This list was generated after the
fact so I may have missed something.

## Dependencies

Nanopb and Pigweed are managed through CMake's `FetchContent`.

This prototype is now running on top of my WIP patch
(https://pwrev.dev/417632) to add Python protobuf codegen to the
CMake build. This change will reduce a lot of boilerplate complexity
in the prototype's `CMakeLists.txt`.

## Build

```
./build.sh
```

## Run

1. Open a console tab and run `./build/rpc_demo`.

   The app boots up and starts listening on `localhost:33001`.

2. Open another console tab, `cd` into the root of the Pigweed repo, bootstrap,
   and then start a `pw_console` session so that you can test sending an
   RPC to the app.

   ```
   cd third_party/pigweed
   . bootstrap.sh
   python3 ../../../run_console.py --socket-addr localhost:33001
   ```

   We are only using bootstrap here to simplify the client-side
   manual testing part of the prototype. I haven't investigated
   how to set up client-side without bootstrap.

3. In the Python REPL of `pw_console` send an RPC to the app.

   ```
   device.rpcs.rpc.ping.PingService.Ping(value="rpc")
   ```

4. In the console tab running the app, you should see `rpc` printed to
   `stdout`.

## Architecture

`main.cc` is an RPC server. It uses `pw_rpc::system_server` (configured with
the `host` backend), which listens on a TCP socket. Communication over the
socket uses HDLC framing (`pw_hdlc`).

All protobufs are generated during the CMake build.

`pw_console` is the client used for manual testing.

### Files

Source files:

*   `//CMakeLists.txt`: Defines the CMake build system. It fetches dependencies
    (Nanopb, Pigweed), configures Pigweed backends, manually bootstraps
    Pigweed-internal Python protos needed by plugins, uses `pw_proto_library`
    for C++ proto generation, and defines the `rpc_demo` executable target.

*   `//main.cc`: The entry point for the C++ application. It initializes the
    Pigweed system server, registers the `PingService`, and starts the server.

*   `//ping.proto`: Defines the Protocol Buffer service `PingService` with a
    `Ping` method.

*   `//ping.options`: Nanopb options file for `ping.proto`, specifying
    configuration like max size of fields.

*   `//ping_service.h`: Implements the `PingService` defined in `ping.proto`.

*   `//run_console.py`: Python script to launch `pw_console` configured to talk
    to the running application. It sets up the python path to include generated
    protos.

*   `//build.sh`: Bash script to run the build. It configures CMake (if not
    already done) and builds the `rpc_demo` target.

*   `//install.sh`: Bash script to install system dependencies (on Debian-based
    systems).

Generated files:

*   `//build/ping/nanopb/ping.pb.h` and `//build/ping/nanopb/ping.pb.c`: Nanopb
    generated C code for the `ping.proto` messages.

*   `//build/ping/nanopb_rpc/ping.rpc.pb.h`: Pigweed RPC generated C++ header for the
    `ping.proto` service.

*   `//build/generated_python/ping_pb2.py`: Python protobuf module generated
    from `ping.proto`, used by `run_console.py`.

*   `//build/python_packages/`: Contains Python protobuf modules generated from
    Pigweed internal protos, required by Pigweed RPC plugins.
