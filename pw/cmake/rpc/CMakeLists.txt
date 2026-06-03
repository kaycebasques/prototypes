cmake_minimum_required(VERSION 3.20)
project(rpc-demo C CXX)

# 1. Fetch Nanopb
include(FetchContent)
FetchContent_Declare(
  nanopb
  GIT_REPOSITORY https://github.com/nanopb/nanopb.git
  GIT_TAG nanopb-0.4.9.1
)
FetchContent_MakeAvailable(nanopb)

set(dir_pw_third_party_nanopb "${nanopb_SOURCE_DIR}" CACHE PATH "" FORCE)

# 2. Declare Pigweed
FetchContent_Declare(
  pigweed
  GIT_REPOSITORY https://pigweed.googlesource.com/pigweed/pigweed
  GIT_TAG 7629bd6d570e41457a4f50bc1291840cd97c0d15
)

# 3. Configure Pigweed backends.
# We must set these backend variables in the CMake CACHE before calling
# FetchContent_MakeAvailable(pigweed). This is because MakeAvailable automatically
# calls add_subdirectory(), which defines Pigweed targets that depend on these
# backends. Setting them here avoids the need to use the deprecated
# FetchContent_Populate() pattern to retrieve the source path before adding the
# subdirectory.
set(pw_log_BACKEND "pw_log_basic" CACHE STRING "" FORCE)
set(pw_assert.check_BACKEND "pw_assert_basic.check_backend" CACHE STRING "" FORCE)
set(pw_assert.assert_BACKEND "pw_assert.print_and_abort_assert_backend" CACHE STRING "" FORCE)
set(pw_assert_basic.handler_BACKEND "pw_assert_basic.basic_handler" CACHE STRING "" FORCE)
set(pw_sys_io_BACKEND "pw_sys_io_stdio" CACHE STRING "" FORCE)
set(pw_sync.mutex_BACKEND "pw_sync_stl.mutex_backend" CACHE STRING "" FORCE)
set(pw_sync.interrupt_spin_lock_BACKEND "pw_sync_stl.interrupt_spin_lock" CACHE STRING "" FORCE)
set(pw_chrono.system_clock_BACKEND "pw_chrono_stl.system_clock" CACHE STRING "" FORCE)
set(pw_thread.sleep_BACKEND "pw_thread_stl.sleep" CACHE STRING "" FORCE)
set(pw_thread.id_BACKEND "pw_thread_stl.id" CACHE STRING "" FORCE)
set(pw_thread.thread_BACKEND "pw_thread_stl.thread" CACHE STRING "" FORCE)
set(pw_thread.yield_BACKEND "pw_thread_stl.yield" CACHE STRING "" FORCE)
set(pw_rpc.system_server_BACKEND "targets.host.system_rpc_server" CACHE STRING "" FORCE)

# Disable experimental editions globally for Pigweed proto compiler
set(pw_protobuf_compiler_GENERATE_PROTOS_ARGS "--no-experimental-editions" CACHE STRING "" FORCE)

# 4. Make Pigweed available
FetchContent_MakeAvailable(pigweed)

# 5. Set PIGWEED_DIR for our own use
set(PIGWEED_DIR "${pigweed_SOURCE_DIR}")
set(ENV{PW_ROOT} "${PIGWEED_DIR}")

# Include Pigweed CMake helper
include(${PIGWEED_DIR}/pw_build/pigweed.cmake)
include(${PIGWEED_DIR}/pw_protobuf_compiler/proto.cmake)

# Find protoc
find_program(PROTOC protoc REQUIRED)

# Generate python proto modules needed by Pigweed plugins.
# NOTE: These manual generation steps are required because Pigweed's own
# Python-based protoc plugins (like plugin_nanopb.py) depend on these generated
# Python modules (e.g. codegen_options_pb2.py, packet_pb2.py). In a non-bootstrapped
# CMake build, Pigweed's CMake system does not automatically generate these
# Python modules before they are needed by the plugins, which would cause the
# build to fail with ModuleNotFoundError.
set(PYTHON_PACKAGES_DIR "${CMAKE_CURRENT_BINARY_DIR}/python_packages")
file(MAKE_DIRECTORY ${PYTHON_PACKAGES_DIR}/pw_protobuf_codegen_protos)
file(MAKE_DIRECTORY ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos)

add_custom_command(
  OUTPUT ${PYTHON_PACKAGES_DIR}/pw_protobuf_codegen_protos/codegen_options_pb2.py
  COMMAND ${PROTOC}
          --python_out=${PYTHON_PACKAGES_DIR}
          -I${PIGWEED_DIR}/pw_protobuf
          ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_codegen_protos/codegen_options.proto
  DEPENDS ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_codegen_protos/codegen_options.proto
)

add_custom_command(
  OUTPUT
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/common_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/status_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/field_options_pb2.py
  COMMAND ${PROTOC}
          --python_out=${PYTHON_PACKAGES_DIR}
          -I${PIGWEED_DIR}/pw_protobuf
          ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/common.proto
          ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/status.proto
          ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/field_options.proto
  DEPENDS
    ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/common.proto
    ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/status.proto
    ${PIGWEED_DIR}/pw_protobuf/pw_protobuf_protos/field_options.proto
)

add_custom_command(
  OUTPUT ${PYTHON_PACKAGES_DIR}/pw_rpc/internal/packet_pb2.py
  COMMAND ${PROTOC}
          --python_out=${PYTHON_PACKAGES_DIR}
          -I${PIGWEED_DIR}
          ${PIGWEED_DIR}/pw_rpc/internal/packet.proto
  DEPENDS ${PIGWEED_DIR}/pw_rpc/internal/packet.proto
)

add_custom_target(generate_python_protos
  DEPENDS
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_codegen_protos/codegen_options_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/common_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/status_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_protobuf_protos/field_options_pb2.py
    ${PYTHON_PACKAGES_DIR}/pw_rpc/internal/packet_pb2.py
)

# Add dependency to Pigweed internal proto targets
if(TARGET pw_rpc.protos._generate.pwpb)
  add_dependencies(pw_rpc.protos._generate.pwpb generate_python_protos)
endif()
if(TARGET pw_rpc.protos._generate.nanopb)
  add_dependencies(pw_rpc.protos._generate.nanopb generate_python_protos)
endif()
if(TARGET pw_rpc.protos._generate.nanopb_rpc)
  add_dependencies(pw_rpc.protos._generate.nanopb_rpc generate_python_protos)
endif()

# 6. Declare the proto library.
pw_proto_library(ping
  SOURCES
    ping.proto
  INPUTS
    ping.options
)

# 7. Generate python proto for console.
# NOTE: Pigweed's pw_proto_library in CMake does not support Python code
# generation (unlike the GN version). We need to manually generate python
# protos here because run_console.py requires ping_pb2.py to run the host-side
# interactive console.
set(GENERATED_PYTHON_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_python")
file(MAKE_DIRECTORY ${GENERATED_PYTHON_DIR})

add_custom_command(
  OUTPUT
    ${GENERATED_PYTHON_DIR}/ping_pb2.py
  COMMAND ${PROTOC}
          --python_out=${GENERATED_PYTHON_DIR}
          -I.
          ping.proto
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS ping.proto
)

add_custom_target(generate_python_ping_protos
  DEPENDS
    ${GENERATED_PYTHON_DIR}/ping_pb2.py
)

# 8. Define Demo Executable
add_executable(rpc_demo main.cc)
target_link_libraries(rpc_demo
  PRIVATE
    ping.nanopb_rpc
    pw_rpc.system_server
    pw_log
)
add_dependencies(rpc_demo generate_python_ping_protos)


