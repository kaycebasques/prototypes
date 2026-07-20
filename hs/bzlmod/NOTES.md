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

## Hermetic Solution

The build is made 100% hermetic out-of-the-box on any Linux machine by applying a Bzlmod patch override (`rules_haskell_bindist.patch`) in `MODULE.bazel`.

1. **Debian 11 GHC Bindist (`deb11`)**:
   Patches `haskell/private/ghc_bindist_generated.json` within `rules_haskell` to point `linux_amd64` GHC 9.4.6 to the Debian 11 binary distribution (`ghc-9.4.6-x86_64-deb11-linux.tar.xz`).

2. **Hermetic Library Bundling (`ghc_bindist.bzl`)**:
   During toolchain setup (`_ghc_bindist_impl`), hermetic Debian packages for `libgmp-dev` (`libgmp.a`, `libgmp.so`, `gmp.h`), `libgmp10` (`libgmp.so.10`), and `libtinfo6` (`libtinfo.so.6` with `libtinfo.so.5` compatibility symlink) are downloaded via immutable snapshot URLs with sha256 checksums.
   - The libraries are placed directly in the GHC toolchain's `lib/lib` directory and GHC's `ghc-bignum` package directory.
   - GHC binary wrappers (`bin/ghc`, `bin/ghc-pkg`, `bin/hsc2hs`, `bin/runghc`) are patched to set `LD_LIBRARY_PATH` to the toolchain's library directories.
   - When GHC/Cabal passes `-L.../ghc-bignum-1.3 -lgmp` during linking, the linker resolves `libgmp.a` / `libgmp.so` directly within the Bazel repository.

3. **Bzlmod Override (`MODULE.bazel`)**:
   Uses `single_version_override` to apply the patch whenever `rules_haskell` is fetched:

   ```starlark
   single_version_override(
       module_name = "rules_haskell",
       patches = ["//:rules_haskell_bindist.patch"],
       patch_strip = 1,
   )
   ```

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
