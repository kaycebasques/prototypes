# Hermetic Haskell Bazel Build Architecture & Reference

## Overview
This repository (`hs/bzlmod`) provides a **100% hermetic Haskell build** in Bazel using `bzlmod`. The build operates cleanly without requiring Nix, legacy `WORKSPACE` files, host-installed Haskell toolchains (`ghc`, `cabal`, `stack`, `ghcup`), or host system C development libraries (`libgmp-dev`, `libtinfo-dev`, `zlib1g-dev`).

---

## 1. Current Architecture

```
                                  +-------------------+
                                  |   MODULE.bazel    |
                                  +---------+---------+
                                            |
                  +-------------------------+-------------------------+
                  |                                                   |
      [archive_override]                                    [use_extension]
  tweag/rules_haskell (master)                                 //:non_module_deps.bzl
                  |                                                   |
        (native deb11 selection)                          +-----------+-----------+
  haskell_toolchains.bindists(dist="deb11")               |                       |
                  |                                   @zlib.dev//:zlib        @gmp//:gmp
                  v                                       |                       |
       GHC 9.4.6 (Debian 11)                              +-----------+-----------+
    Bundled libtinfo6 & libgmp                                        |
                  |                                                   v
                  +---------------------------------------> stack.package(name="zlib",
                                                              extra_deps=["@zlib.dev", "@gmp"])
                                                                      |
                                                                      v
                                                            //:example (Haskell Binary)
```

### Key Architectural Components:

1. **Pure Bzlmod Setup (`MODULE.bazel`)**:
   - The project uses `MODULE.bazel` exclusively. The `WORKSPACE` file is empty (`# Empty WORKSPACE file for bzlmod project`).
   - Bazel version is pinned to `6.5.0` via `.bazelversion` due to `rules_haskell`'s reliance on Bazel 6.x Starlark C++ toolchain APIs.

2. **Upstream Bzlmod Override (`archive_override`)**:
   - Uses `archive_override` to pin `rules_haskell` to upstream master (`https://github.com/tweag/rules_haskell/archive/refs/heads/master.tar.gz`).
   - This provides native support for selecting Linux distributions via the `dist` attribute in `haskell_toolchains.bindists`.

3. **Debian 11 GHC Bindist (`deb11`)**:
   - GHC `9.4.6` is downloaded using the official Debian 11 binary distribution (`deb11`).
   - Debian 11 GHC binaries dynamically link against `ncurses 6` (`libtinfo.so.6`), avoiding runtime library missing errors on modern Linux distros (Debian 12, Ubuntu 22.04+, RHEL/Fedora, Arch).

4. **Hermetic C Dependencies (`non_module_deps.bzl`)**:
   - **`@zlib.dev//:zlib`**: Downloads `zlib-1.3` source and builds static `libz.a` hermetically via `zlib.BUILD.bazel`.
   - **`@gmp//:gmp`**: Downloads Debian's `libgmp-dev` and `libgmp10` deb packages and extracts `libgmp.a`/`libgmp.so` and `gmp.h` into `@gmp//:gmp`.
   - Both dependencies are passed as `extra_deps` to `stack.package` for Hackage packages (`@stackage//:zlib`).

---

## 2. Workarounds Currently In Use

1. **`archive_override` for BCR 1.0 Feature Gap**:
   - *Issue*: The official `1.0` release tag published on Bazel Central Registry (BCR) hardcodes GHC downloads to Debian 9 (`deb9`) and lacks the `dist` attribute in `haskell_toolchains.bindists`.
   - *Workaround*: We use `archive_override` in `MODULE.bazel` to fetch upstream `master`, giving us native `dist = {"linux_amd64": "deb11"}` without applying local source patches.

2. **Hermetic `@gmp//:gmp` Repository for `ghc-bignum`**:
   - *Issue*: GHC's core package `ghc-bignum` requests `-lgmp` during linker phases (`hsc2hs` / `CabalLibrary`). On minimal Linux machines without `libgmp-dev` on the host OS, `/usr/bin/ld: cannot find -lgmp` fails the build.
   - *Workaround*: `non_module_deps.bzl` fetches and unpacks Debian's GMP packages into a hermetic `@gmp//:gmp` repository, which is supplied to `stack.package(extra_deps = ["@gmp//:gmp", ...])`.

---

## 3. Alternative Approaches Attempted & Why They Were Rejected

1. **Patching `rules_haskell` Source Files (`single_version_override`)**:
   - *Attempted*: Created a patch file (`rules_haskell_bindist.patch`) and applied it via `single_version_override(module_name = "rules_haskell", patches = [...])`.
   - *Why Rejected*: High maintenance burden. Patch files break whenever `rules_haskell` updates upstream, and the user explicitly requested avoiding source patches.

2. **Local Directory Overrides (`local_path_override`)**:
   - *Attempted*: Used `local_path_override` pointing to a local git clone (`tmp/rules_haskell`).
   - *Why Rejected*: Non-reproducible across different developer machines and CI pipelines. Requires manual pre-cloning steps outside Bazel.

3. **Custom Workspace Toolchain Extension (`ghc_toolchains.bzl`)**:
   - *Attempted*: Wrote a custom repository rule to download GHC Debian 11, run `./configure --prefix && make install`, patch binary wrapper paths, and invoke `pkgdb_to_bzl.py`.
   - *Why Rejected*: High complexity (~150 lines of Starlark logic). Required manual handling for GHC's internal `package.conf.d` and `docdir` paths. `archive_override` replaced it with 0 lines of custom toolchain code.

---

## 4. Gotchas & Problems to Watch Out For

1. **Clean Developer / CI Machines without `libgmp-dev`**:
   - Always ensure any C library required by GHC core packages (`-lgmp`) or Hackage packages (`-lz`) is declared in `non_module_deps.bzl` and included in `stack.package`'s `extra_deps`.

2. **BCR Release vs Upstream Master**:
   - Until `rules_haskell` publishes a `1.1`+ release to Bazel Central Registry containing the `dist` tag class, projects on modern Linux must use `archive_override` or `git_override` to select `deb11`.

3. **GHC Package Database & Haddock Structure**:
   - GHC 9.4+ reorganizes library paths under `lib/x86_64-linux-ghc-*`. If creating custom toolchain rules, `pkgdb_to_bzl.py` requires `docdir_path` or valid symlinks to `package.conf.d` and `doc/html/libraries/base-*`.

---

## 5. Verification & Hermeticity Proof

Hermeticity can be verified on any machine by running:

```bash
python3 hermetic.py
```

The verification script executes a two-phase check:
1. **Phase 1 (`bazelisk aquery`)**: Inspects all 2,300+ actions in the build graph to confirm that no host tool paths (`/usr/bin/ghc`, `~/.ghcup`, `~/.cabal`) or host system libraries (`/usr/lib`, `/usr/local/lib`) are accessed.
2. **Phase 2 (`bazelisk run`)**: Executes `bazelisk run //:example` under a sanitized minimal environment (`PATH`, `HOME`, `USER` only), confirming clean compilation and execution.
