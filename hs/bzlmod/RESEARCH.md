# Research Report: Hermetic Haskell Builds in Bazel (Bzlmod)

## Executive Summary

This research report investigates two core questions regarding the Haskell Bazel build setup in `hs/bzlmod`:

1. **GHC Bindist & Debian 11 Selection**: You **do not** need to patch `rules_haskell` or override GHC download URLs to use Debian 11. `rules_haskell` natively provides a `dist` attribute in its Bzlmod extension (`haskell_toolchains.bindists(dist = {"linux_amd64": "deb11"})`) that selects the pre-indexed Debian 11 GHC bindist out-of-the-box.
2. **Hermetic Linkers & Pigweed Host Toolchain**: `rules_haskell` delegates all C compilation and linking to Bazel's registered C/C++ toolchain via `@rules_cc//cc:find_cc_toolchain.bzl`. Registering Pigweed's `host_cc_toolchain_linux` provides **100% hermetic access to Clang and LLD**, completely eliminating dependencies on host `/usr/bin/gcc`, `/usr/bin/ld.bfd`, or `/usr/bin/ar`. However, because Pigweed's toolchain is a general C/C++ toolchain, it does not include Haskell-specific domain libraries like `libgmp`. To eliminate all patches to `rules_haskell`, `libgmp` can be supplied hermetically via standard Bazel repository rules or bypassed entirely using GHC's native integer backend.

---

## 1. Topic 1: GHC Bindist Selection in `rules_haskell`

### The Problem in Current Setup
In [NOTES.md](file:///usr/local/google/home/kayce/prototypes/hs/bzlmod/NOTES.md), the build applies a patch ([rules_haskell_bindist.patch](file:///usr/local/google/home/kayce/prototypes/hs/bzlmod/rules_haskell_bindist.patch)) to `haskell/private/ghc_bindist_generated.json` to swap the default Linux GHC 9.4.6 download URL from Debian 9 (`deb9`) to Debian 11 (`deb11`).

### Codebase Findings
Inspection of the `rules_haskell` codebase reveals why `deb9` was selected by default and how `rules_haskell` is designed to be configured:

1. **Debian 11 is Already Indexed in `rules_haskell`**:
   Upstream `haskell/private/ghc_bindist_generated.json` already contains full metadata (URL and SHA256 checksum) for Debian 11 for GHC 9.4.6:
   ```json
   "9.4.6": {
       "linux_amd64": [
           {
               "dist": "deb11",
               "sha256": "43da1a641307fcd97b324648adcd39b673b94ab61507b5639038b36abf938569",
               "url": "https://downloads.haskell.org/~ghc/9.4.6/ghc-9.4.6-x86_64-deb11-linux.tar.xz"
           },
           ...
       ]
   }
   ```

2. **Why `deb9` Was Selected by Default**:
   In `haskell/ghc_bindist.bzl` (lines 99–107), when no `dist` attribute is specified by the user, `rules_haskell` executes the following fallback logic:
   ```starlark
   if os.startswith("linux"):
       # for Linux, we use debian dists by default
       debian_dists = sorted([int(d[3:]) for d in dists if d.startswith("deb")])
       if debian_dists:
           # prefer the oldest version by default
           deb_version = "deb{}".format(debian_dists[0])
           bindists = [bindist for bindist in bindists if bindist["dist"] == deb_version]
   ```
   Because `deb9` is the oldest Debian release listed (`sorted([9, 10, 11])[0] == 9`), `rules_haskell` defaults to `deb9` for backwards compatibility with older glibc systems. On modern Linux distros, `deb9` binaries fail to run because they require `libtinfo.so.5` (ncurses 5), whereas modern distributions ship with `libtinfo.so.6` (ncurses 6).

3. **The Built-in, Patch-Free Solution**:
   Both the `haskell_toolchains.bindists` and `haskell_toolchains.bindist` tag classes in `extensions/haskell_toolchains.bzl` expose a `dist` attribute (`attr.string_dict`).

   In [MODULE.bazel](file:///usr/local/google/home/kayce/prototypes/hs/bzlmod/MODULE.bazel), you can specify `deb11` directly:
   ```starlark
   haskell_toolchains = use_extension(
       "@rules_haskell//extensions:haskell_toolchains.bzl",
       "haskell_toolchains",
   )

   haskell_toolchains.bindists(
       version = "9.4.6",
       dist = {
           "linux_amd64": "deb11",
       },
   )
   ```
   Setting `dist = {"linux_amd64": "deb11"}` immediately forces `rules_haskell` to download the Debian 11 bindist without patching any `rules_haskell` source files.

---

## 2. Topic 2: Missing Linkers & Pigweed Host Toolchain Integration

### The Problem in Current Setup
When building Haskell binaries or Stackage packages (e.g. `@stackage//:zlib`), GHC relies on a C compiler and linker to assemble object files and link executables. On clean Linux systems without build tools installed (`build-essential`, `gcc`, `ld`), builds fail due to missing system linkers or missing C development libraries (`cannot find -lgmp`).

### How `rules_haskell` Interacts with C/C++ Toolchains
Inspection of `haskell/private/cc_wrapper.bzl` and `haskell/cc.bzl` demonstrates how `rules_haskell` invokes the C compiler and linker:

1. **Toolchain Resolution via `@rules_cc`**:
   `rules_haskell` defines a wrapper script (`cc_wrapper`) passed to GHC via `-pgmc` (C compiler), `-pgml` (linker), and `-pgma` (assembler).
2. **Automatic Delegation to Bazel's Registered `cc_toolchain`**:
   `cc_wrapper` uses `@rules_cc//cc:find_cc_toolchain.bzl` (`find_cc_toolchain(ctx)`) to query Bazel's active C/C++ toolchain:
   ```starlark
   cc_toolchain = find_cc_toolchain(ctx)
   cc = cc_common.get_tool_for_action(feature_configuration, action_name = ACTION_NAMES.c_compile)
   ar = cc_common.get_tool_for_action(feature_configuration, action_name = ACTION_NAMES.cpp_link_static_library)
   ```
   **Crucial Insight**: `rules_haskell` does not hardcode `/usr/bin/gcc` or `/usr/bin/ld`. It automatically delegates all C compilation and linking actions to whatever C/C++ toolchain is registered in Bazel.

### Can We Use Pigweed's Host Toolchain?
Inspection of `tmp/pigweed` (`pw_toolchain/host_clang/BUILD.bazel` and `pw_toolchain/cc/pw_cxx_toolchain.bzl`) reveals the capabilities and boundaries of Pigweed's host toolchain:

#### 1. What Pigweed's Host Toolchain Solves (Hermetic Compiler & Linker)
Pigweed registers `host_cc_toolchain_linux` using prebuilt LLVM/Clang binaries fetched via CIPD:
- **C/C++ Compiler**: Hermetic `clang` / `clang++`
- **Linker**: Hermetic `lld` (configured via `-fuse-ld=lld`)
- **Archiver & Utilities**: Hermetic `llvm-ar`, `llvm-nm`, `llvm-objcopy`, `llvm-strip`
- **Standard Runtime**: `libc++`, `compiler-rt`, `libunwind`, and a basic Linux sysroot

When Pigweed's host C++ toolchain is registered in `MODULE.bazel`:
```starlark
register_toolchains("@pigweed//pw_toolchain/host_clang:host_cc_toolchain_linux")
```
`rules_haskell`'s `cc_wrapper` automatically invokes Pigweed's `clang` and `lld`. This completely eliminates any requirement for host-installed `/usr/bin/gcc`, `/usr/bin/ld.bfd`, or `binutils`.

#### 2. What Pigweed's Host Toolchain Does Not Include (GMP & Haskell Domain Libraries)
While Pigweed provides the compiler, linker, and standard C library headers, it is a general embedded/host C++ toolchain. It does not package third-party domain libraries required by Haskell packages:
- **`libgmp`**: GHC's core integer library (`ghc-bignum`) passes `-lgmp` to the linker. Neither Pigweed nor standard LLVM toolchains bundle `libgmp.a` / `libgmp.so`.
- **`libtinfo`**: GHC host binaries (`ghc`, `ghc-pkg`) require `libtinfo.so.6` at host runtime.

---

## 3. Hermetic Dependency Architecture

To achieve a 100% hermetic Haskell build without patching `rules_haskell`, the build requirements break down into three distinct layers:

```
+-------------------------------------------------------------------------------+
|                             BAZEL BUILD GRAPH                                 |
+-------------------------------------------------------------------------------+
                                       |
       +-------------------------------+-------------------------------+
       |                               |                               |
       v                               v                               v
[ Layer 1: GHC Bindist ]    [ Layer 2: C/C++ Toolchain ]    [ Layer 3: C Libraries ]
  - GHC 9.4.6 (Debian 11)     - Pigweed / LLVM Toolchain      - Hermetic libgmp
  - Configured via `dist`     - Clang + LLD Linker            - Hermetic zlib.dev
  - No patches required       - Replaces /usr/bin/ld          - Passed via extra_deps
```

| Layer | Responsibility | Hermetic Solution (No `rules_haskell` Patches) |
|---|---|---|
| **1. GHC Binaries** | GHC compiler and package tools (`ghc`, `ghc-pkg`) | Use `dist = {"linux_amd64": "deb11"}` in `MODULE.bazel`. |
| **2. C Compiler & Linker** | Compiling C stubs and linking Haskell binaries | Register Pigweed's `host_cc_toolchain_linux` or `@toolchains_llvm`. |
| **3. C Dependencies** | Providing `-lgmp` and `-lz` to the linker | Supply `@gmp` and `@zlib.dev` via Bazel repo rules or use GHC native integer variant. |

---

## 4. Recommended Solutions to Eliminate All Patches

### Solution A: Pigweed / LLVM Toolchain + Hermetic `@gmp` Repository (Recommended)

This approach retains standard GHC (with GMP-accelerated bignums) while making all toolchains and libraries hermetic using standard Bazel repository rules.

#### Step 1: Configure `MODULE.bazel`
Remove `single_version_override` on `rules_haskell`. Configure Debian 11 bindist, register the hermetic C++ toolchain (Pigweed or LLVM), and declare hermetic C library repositories:

```starlark
module(name = "hs_bzlmod", version = "0.1")

bazel_dep(name = "rules_haskell", version = "1.0")
bazel_dep(name = "rules_cc", version = "0.0.9")
bazel_dep(name = "pigweed")  # Or toolchains_llvm

# 1. Select Debian 11 bindist natively (no patches)
haskell_toolchains = use_extension(
    "@rules_haskell//extensions:haskell_toolchains.bzl",
    "haskell_toolchains",
)
haskell_toolchains.bindists(
    version = "9.4.6",
    dist = {
        "linux_amd64": "deb11",
    },
)

# 2. Register Pigweed's hermetic host C/C++ toolchain (provides clang & lld)
register_toolchains("@pigweed//pw_toolchain/host_clang:host_cc_toolchain_linux")

# 3. Hermetic C library dependencies (GMP, Zlib)
non_module_deps = use_extension("//:non_module_deps.bzl", "non_module_deps")
use_repo(non_module_deps, "zlib.dev", "gmp.dev")

# 4. Stackage package configuration
stack = use_extension("@rules_haskell//extensions:stack_snapshot.bzl", "stack_snapshot")
use_repo(stack, "stackage")

stack.package(
    name = "zlib",
    extra_deps = ["@zlib.dev//:zlib"],
)
stack.snapshot(name = "lts-21.5")
```

#### Step 2: Hermetic GMP Repository (`non_module_deps.bzl`)
Instead of patching `rules_haskell`'s repository rule to download Debian `.deb` files into the GHC installation directory, fetch precompiled static libraries (`libgmp.a` + `gmp.h`) or build GMP from source via `http_archive` / `rules_foreign_cc` in your own workspace:

```starlark
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def _non_module_deps_impl(_mctx):
    http_archive(
        name = "zlib.dev",
        build_file = "//:zlib.BUILD.bazel",
        sha256 = "b5b06d60ce49c8ba700e0ba517fa07de80b5d4628a037f4be8ad16955be7a7c0",
        strip_prefix = "zlib-1.3",
        urls = ["https://github.com/madler/zlib/archive/v1.3.tar.gz"],
    )
    http_archive(
        name = "gmp.dev",
        build_file = "//:gmp.BUILD.bazel",
        urls = ["https://.../gmp-prebuilt-x86_64.tar.gz"],
    )

non_module_deps = module_extension(implementation = _non_module_deps_impl)
```

---

### Solution B: GHC Native Integer / Static Variant (Zero GMP Dependency)

If your build does not strictly require GNU MP for high-performance arbitrary-precision arithmetic, GHC provides official bindists using a native Haskell integer implementation (`ghc-bignum` native backend).

#### How to Configure in `MODULE.bazel`:
```starlark
haskell_toolchains = use_extension(
    "@rules_haskell//extensions:haskell_toolchains.bzl",
    "haskell_toolchains",
)

haskell_toolchains.bindists(
    version = "9.4.6",
    dist = {
        "linux_amd64": "alpine3_12",
    },
    variant = {
        "linux_amd64": "static-int_native",
    },
)
```

#### Key Benefits:
- **No GMP Requirement**: GHC links zero `-lgmp` flags.
- **Fully Static Host Binaries**: Alpine musl static bindists are statically linked and have no runtime dependencies on host `glibc` or `libtinfo.so`.

---

## 5. Summary of Findings & Next Steps

| Question | Answer | Action |
|---|---|---|
| **Must we patch GHC download URLs for Debian 11?** | **No.** `rules_haskell` natively supports `dist = {"linux_amd64": "deb11"}` in Bzlmod. | Remove `ghc_bindist_generated.json` patch; add `dist` attribute to `haskell_toolchains.bindists`. |
| **Can we use Pigweed's host toolchain for linkers?** | **Yes.** `rules_haskell` automatically queries Bazel's registered `cc_toolchain`, routing all linking through Pigweed's `clang` and `lld`. | Register Pigweed's host C++ toolchain in `MODULE.bazel`. |
| **How to handle missing `libgmp` without patching?** | Declare hermetic C library repos (`@gmp.dev`) in workspace module extensions, or switch to GHC's `native` integer variant. | Remove `ghc_bindist.bzl` deb download patch; supply GMP via Bazel repo rule or native integer variant. |
