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

FetchContent_Declare(
  pigweed
  GIT_REPOSITORY https://github.com/kaycebasques/pigweed.git
  GIT_TAG d729c05d905872b3ed1a763219fbcc95b4fc26ee
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

set(pw_protobuf_compiler_PYTHON_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated_python" CACHE PATH "" FORCE)

# 4. Make Pigweed available
FetchContent_MakeAvailable(pigweed)

# 5. Set PIGWEED_DIR for our own use
set(PIGWEED_DIR "${pigweed_SOURCE_DIR}")
set(ENV{PW_ROOT} "${PIGWEED_DIR}")

# Include Pigweed CMake helper
include(${PIGWEED_DIR}/pw_build/pigweed.cmake)
include(${PIGWEED_DIR}/pw_protobuf_compiler/proto.cmake)

# Define a target to group all python protos needed for the console.
add_custom_target(generate_python_protos
  DEPENDS
    ping.python
    pw_protobuf.codegen_protos.python
    pw_protobuf.common_proto.python
    pw_protobuf.status_proto.python
    pw_protobuf.field_options_proto.python
    pw_rpc.protos.python
)

# Ensure Pigweed internal proto generation has access to generated python protos
# needed by its plugins.
if(TARGET pw_rpc.protos._generate.pwpb)
  add_dependencies(pw_rpc.protos._generate.pwpb
    pw_protobuf.codegen_protos.python
    pw_protobuf.common_proto.python
    pw_protobuf.status_proto.python
    pw_protobuf.field_options_proto.python
  )
endif()
if(TARGET pw_rpc.protos._generate.nanopb)
  add_dependencies(pw_rpc.protos._generate.nanopb
    pw_protobuf.codegen_protos.python
    pw_protobuf.common_proto.python
    pw_protobuf.status_proto.python
    pw_protobuf.field_options_proto.python
  )
endif()
if(TARGET pw_rpc.protos._generate.nanopb_rpc)
  add_dependencies(pw_rpc.protos._generate.nanopb_rpc
    pw_protobuf.codegen_protos.python
    pw_protobuf.common_proto.python
    pw_protobuf.status_proto.python
    pw_protobuf.field_options_proto.python
  )
endif()

# 6. Declare the proto library.
pw_proto_library(ping
  SOURCES
    ping.proto
  INPUTS
    ping.options
)

# 8. Define Demo Executable
add_executable(rpc_demo main.cc)
target_link_libraries(rpc_demo
  PRIVATE
    ping.nanopb_rpc
    pw_rpc.system_server
    pw_log
)
add_dependencies(rpc_demo generate_python_protos)


