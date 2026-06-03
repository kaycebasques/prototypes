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

# 6. Find protoc
find_program(PROTOC protoc REQUIRED)

# 7. Generate python proto modules needed by Pigweed plugins
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

# 8. Manual Proto Generation Setup for User Proto
set(GENERATED_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY ${GENERATED_DIR})

set(GENERATED_PYTHON_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_python")
file(MAKE_DIRECTORY ${GENERATED_PYTHON_DIR})

# Construct PYTHONPATH for Pigweed RPC plugin
set(PW_PYTHON_PATH
  ${PYTHON_PACKAGES_DIR}
  ${PIGWEED_DIR}/pw_rpc/py
  ${PIGWEED_DIR}/pw_status/py
  ${PIGWEED_DIR}/pw_protobuf/py
  ${PIGWEED_DIR}/pw_protobuf_compiler/py
  ${PIGWEED_DIR}/pw_stream/py
  ${PIGWEED_DIR}/pw_log/py
)
string(REPLACE ";" ":" PW_PYTHON_PATH_STR "${PW_PYTHON_PATH}")

# Command to generate nanopb .pb.h/.pb.c
add_custom_command(
  OUTPUT
    ${GENERATED_DIR}/ping.pb.h
    ${GENERATED_DIR}/ping.pb.c
  COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${nanopb_SOURCE_DIR}/generator"
          ${PROTOC}
          --plugin=protoc-gen-nanopb=${nanopb_SOURCE_DIR}/generator/protoc-gen-nanopb
          --nanopb_out=${GENERATED_DIR}
          -I.
          ping.proto
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS ping.proto ping.options
)

# Command to generate pw_rpc .rpc.pb.h
add_custom_command(
  OUTPUT
    ${GENERATED_DIR}/ping.rpc.pb.h
  COMMAND ${CMAKE_COMMAND} -E env "PYTHONPATH=${PW_PYTHON_PATH_STR}"
          ${PROTOC}
          --plugin=protoc-gen-custom=${PIGWEED_DIR}/pw_rpc/py/pw_rpc/plugin_nanopb.py
          --custom_out=${GENERATED_DIR}
          -I.
          ping.proto
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS ping.proto ${GENERATED_DIR}/ping.pb.h
)

# Command to generate python proto
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

# Create library for generated protos
add_library(ping_protos STATIC
  ${GENERATED_DIR}/ping.pb.c
  ${GENERATED_DIR}/ping.pb.h
  ${GENERATED_DIR}/ping.rpc.pb.h
)
target_include_directories(ping_protos PUBLIC ${GENERATED_DIR})
target_link_libraries(ping_protos
  PUBLIC
    protobuf-nanopb-static
    pw_rpc.nanopb.server_api
    pw_rpc.server
)

# 9. Define Demo Executable
add_executable(rpc_demo main.cc)
target_link_libraries(rpc_demo
  PRIVATE
    ping_protos
    pw_rpc.system_server
    pw_log
)
add_dependencies(rpc_demo generate_python_protos generate_python_ping_protos)

