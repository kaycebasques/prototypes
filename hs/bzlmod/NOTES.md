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

## Verification
You can clone this repository on any modern Linux machine and build/run
targets out of the box with zero host package prerequisites:

```bash
cd hs/bzlmod
bazelisk run //:example
```
