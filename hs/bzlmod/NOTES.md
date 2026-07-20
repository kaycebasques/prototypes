# Haskell Bazel Build Setup (Bzlmod)

## Overview
The Bazel build in `hs/bzlmod` is configured using `bzlmod` with `rules_haskell` 1.0. It provides a fully hermetic Haskell build without requiring Nix, legacy `WORKSPACE` files, or host-installed Haskell toolchains (`ghc`, `cabal`, `stack`, `ghcup`) or system C libraries (`libgmp-dev`, `libtinfo-dev`).

Bazel version is pinned to `6.5.0` via `.bazelversion` because `rules_haskell` 1.0 relies on Bazel 6.x Starlark C++ toolchain APIs (newer Bazel versions like 9.x removed legacy Starlark symbols such as `CcInfo`).

## Issues Encountered on Clean Linux Systems

When running `rules_haskell` out-of-the-box on clean Linux machines, two host library dependency issues arise:

### 1. `libtinfo.so.5` (GHC Binary Wrapper Failures)
By default, `rules_haskell` downloads precompiled GHC binary distributions (bindists) built for older Debian 9 Linux (`ghc-9.4.6-x86_64-deb9-linux.tar.xz`). During toolchain extraction and installation (`make install`), the GHC package registration tool (`ghc-pkg`) fails on modern Linux systems because it is dynamically linked against `ncurses 5` (`libtinfo.so.5`):

```
ghc-pkg: error while loading shared libraries: libtinfo.so.5:
cannot open shared object file: No such file or directory
```

Modern Linux distributions (Debian 12, Ubuntu 22.04+, RHEL/Fedora, Arch) ship with `ncurses 6` (`libtinfo.so.6`).

### 2. `cannot find -lgmp` (Cabal & Linker Failures on Clean Machines)
When building Hackage packages (`@stackage//:zlib`) or linking Haskell binaries (`//:example`), GHC's core `ghc-bignum` package passes `-lgmp` to the C linker (`ld`). On machines without host development packages installed (`sudo apt install libgmp-dev`), the build fails with:

```
/usr/bin/x86_64-linux-gnu-ld.bfd: cannot find -lgmp: No such file or directory
collect2: error: ld returned 1 exit status
`gcc' failed in phase `Linker'. (Exit code: 1)
```

## Hermetic Solution (100% Bzlmod, Patch-Free)

The build is configured entirely in `MODULE.bazel` without any legacy `WORKSPACE` files, custom toolchain macros, or source patches:

1. **Bzlmod Module Override (`archive_override`)**:
   `MODULE.bazel` pins `rules_haskell` directly to upstream master on GitHub, which contains native multi-distribution bindist support:

   ```starlark
   archive_override(
       module_name = "rules_haskell",
       urls = ["https://github.com/tweag/rules_haskell/archive/refs/heads/master.tar.gz"],
       strip_prefix = "rules_haskell-master",
   )
   ```

2. **Native Debian 11 GHC Bindist (`deb11`)**:
   With upstream's native `dist` attribute, `MODULE.bazel` directly selects the Debian 11 binary distribution for GHC 9.4.6:

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

3. **Zero Patch Overrides & Zero Host Tool Dependencies**:
   The Debian 11 bindist dynamically links against `ncurses 6` (`libtinfo.so.6`), which is standard on modern Linux systems. Zero patch files (`single_version_override`) or host Haskell toolchains are needed.

## Verification & Hermeticity Proof

You can verify the hermeticity of the build on any Linux machine by running `hermetic.py`:

```bash
cd hs/bzlmod
python3 hermetic.py
```

The script proves hermeticity through a two-phase verification process:

1. **Action Graph Inspection (`bazelisk aquery`)**
   - Queries the build graph (`bazelisk aquery --output=jsonproto "deps(//:example)"`) to inspect all actions, toolchains, executables, environment variables, and input artifacts.
   - **Haskell Toolchains & Compilers**: Confirms that GHC, `ghc-pkg`, and related toolchain paths (`RULES_HASKELL_GHC_PATH`, `RULES_HASKELL_GHC_PKG_PATH`, `RULES_HASKELL_LIBDIR_PATH`, etc.) resolve exclusively to Bazel-managed external repositories (`external/rules_haskell...`) and not to host Haskell paths (`/usr/bin/ghc`, `~/.ghcup`, `~/.cabal`, `~/.stack`, `/nix/store`, or `/opt/ghc`).
   - **Executables & Command Arguments**: Verifies that actions invoke Bazel-managed wrappers (`ghc_wrapper`, `cabal_wrapper`) or bindist binaries, and that action arguments contain no unmanaged host library or search flags.
   - **Input Artifacts & Library Dependencies**: Resolves all input artifacts across Haskell and linking actions to verify that all Haskell packages (`base`, `bytestring`, `zlib`, `rts`), interface files (`.hi`), package configs (`.conf.d`), and C dependencies (`zlib.dev` / `libz.a`) are Bazel-managed artifacts, with zero inputs originating from host system library paths (`/usr/lib`, `/usr/local/lib`, `/lib64`, `~/.ghc`, etc.).

2. **Sanitized Minimal-Environment Build & Execution (`bazelisk run`)**
   - Strips all host Haskell and toolchain environment variables (`GHC*`, `CABAL*`, `STACK*`, `NIX*`, `HASKELL*`) to create a minimal environment (`PATH`, `HOME`, `USER`).
   - Executes `bazelisk run //:example` to prove that the target compiles, links, and executes successfully without any host Haskell or system development prerequisites, outputting `Hello from rules_haskell!`.
