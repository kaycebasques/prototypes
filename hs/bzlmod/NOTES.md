# Haskell Bazel Build Setup (Bzlmod)

## Overview
The Bazel build in `hs/bzlmod` is configured using `bzlmod` with `rules_haskell`
1.0. It provides a fully hermetic Haskell build without requiring Nix, legacy
`WORKSPACE` files, or host-installed Haskell toolchains.

Bazel version is pinned to `6.5.0` via `.bazelversion` because `rules_haskell`
1.0 relies on Bazel 6.x Starlark C++ toolchain APIs (newer Bazel versions like
9.x removed legacy Starlark symbols such as `CcInfo`).

## Issue Encountered
By default, `rules_haskell` downloads precompiled GHC binary distributions
(bindists) built for older Debian 9 Linux
(`ghc-9.4.6-x86_64-deb9-linux.tar.xz`).

During toolchain extraction and installation (`make install`), the GHC package
registration tool (`ghc-pkg`) fails on modern Linux systems because it is
dynamically linked against `ncurses 5` (`libtinfo.so.5`):

```
ghc-pkg: error while loading shared libraries: libtinfo.so.5:
cannot open shared object file: No such file or directory
```

Modern Linux distributions (Debian 12, Ubuntu 22.04+, and enterprise Linux)
ship with `ncurses 6` (`libtinfo.so.6`).

## Hermetic Solution
The build is made 100% hermetic by applying a Bzlmod patch override to
`rules_haskell` in `MODULE.bazel`.

1. **Patch File (`rules_haskell_bindist.patch`)**
   Patches `haskell/private/ghc_bindist_generated.json` within `rules_haskell`
   to point the `linux_amd64` GHC 9.4.6 bindist to the Debian 11 binary
   distribution (`ghc-9.4.6-x86_64-deb11-linux.tar.xz`). Debian 11 bindists
   are compiled against `libtinfo.so.6` / `glibc 2.31+`.

2. **Bzlmod Override (`MODULE.bazel`)**
   Uses `single_version_override` to apply the patch whenever `rules_haskell`
   is fetched:

   ```starlark
   single_version_override(
       module_name = "rules_haskell",
       patches = ["//:rules_haskell_bindist.patch"],
       patch_strip = 1,
   )
   ```

## Verification & Hermeticity Proof
You can verify the hermeticity of the build on any modern Linux machine by running `hermetic.py`:

```bash
cd hs/bzlmod
python3 hermetic.py
```

The script proves hermeticity through a two-phase verification process:

1. **Action Graph Inspection (`bazelisk aquery`)**
   - Queries the build graph (`bazelisk aquery --output=jsonproto "deps(//:example)"`) to inspect all actions, toolchains, executables, environment variables, and input artifacts.
   - **Haskell Toolchains & Compilers**: Confirms that GHC, `ghc-pkg`, and related toolchain paths (`RULES_HASKELL_GHC_PATH`, `RULES_HASKELL_GHC_PKG_PATH`, `RULES_HASKELL_LIBDIR_PATH`, etc.) resolve exclusively to Bazel-managed external repositories (`external/rules_haskell...`) and not to host Haskell paths (`/usr/bin/ghc`, `~/.ghcup`, `~/.cabal`, `~/.stack`, `/nix/store`, or `/opt/ghc`).
   - **Executables & Command Arguments**: Verifies that actions invoke Bazel-managed wrappers (`ghc_wrapper`, `cabal_wrapper`) or bindist binaries, and that action arguments contain no host tool or library search flags.
   - **Input Artifacts & Library Dependencies**: Resolves all input artifacts across Haskell and linking actions to verify that all Haskell packages (`base`, `bytestring`, `zlib`, `rts`), interface files (`.hi`), package configs (`.conf.d`), and C dependencies (`zlib.dev` / `libz.a`) are Bazel-managed artifacts, with zero inputs originating from host system library paths (`/usr/lib`, `/usr/local/lib`, `/lib64`, `~/.ghc`, etc.).

2. **Sanitized Minimal-Environment Build & Execution (`bazelisk run`)**
   - Strips all host Haskell and toolchain environment variables (`GHC*`, `CABAL*`, `STACK*`, `NIX*`, `HASKELL*`) to create a minimal environment (`PATH`, `HOME`, `USER`).
   - Executes `bazelisk run //:example` to prove that the target compiles, links, and executes successfully without any host Haskell prerequisites, outputting `Hello from rules_haskell!`.

