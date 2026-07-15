# Proving Hermeticity

This document outlines the methods you can use to verify that the Elm application build is fully hermetic and does not rely on host-installed tools or unexpected network access.

## Method 1: Inspecting the Action Graph (`bazel aquery`)

The most precise way to prove hermeticity is to inspect the exact commands Bazel generates and executes. We can use `bazel aquery` (Action Graph Query) to inspect the compilation action for our Elm binary.

Run the following command in the `elm/bzlmod` directory:

```bash
bazelisk aquery //:main_js
```

### What to look for in the output:

1.  **Hermetic Compiler Binary:**
    Find the `Mnemonic: Elm` action. Look at the `Command line` or the `executable` path. It should point to a path inside Bazel's execution root, under the external repository for the Elm compiler, for example:
    `external/elm_x86_64-linux/compiler` (on Linux) or `external/elm_aarch64-darwin/compiler` (on macOS).
    It should **never** point to a system path like `/usr/bin/elm`, `/usr/local/bin/elm`, or a path in your home directory (like `~/.npm/...`).

2.  **Hermetic Inputs:**
    Look at the `Inputs` section of the action. It should list:
    *   The compiler binary from the external repo.
    *   The generated `elm.json` (e.g., `bazel-out/k8-opt-exec/bin/main_js-elm.json`).
    *   The source files of your dependencies, resolved from the external repositories (e.g., `external/elm_package_elm_core/src/Elm/Kernel/Debug.js`, etc.).
    *   It should **not** reference any files outside the Bazel sandbox/execroot.

---

## Method 2: Offline Build Test

This test proves that the build execution phase does not access the network.

1.  **Fetch all external dependencies first:**
    Ensure Bazel has downloaded the compiler and Elm packages:
    ```bash
    bazelisk fetch //...
    ```
2.  **Disconnect from the Internet:**
    Disable your Wi-Fi or unplug your ethernet cable. Alternatively, you can block network access for Bazel by adding `--nofetch` to the build command, which prevents Bazel from trying to fetch any external repos.
3.  **Clean local build outputs:**
    Clean the build cache to force a recompile, but do not clean the external repository cache:
    ```bash
    bazelisk clean
    ```
4.  **Perform the build offline:**
    ```bash
    bazelisk build //... --nofetch
    ```
5.  **Result:** The build should complete successfully. If it does, it proves that the compilation phase is 100% offline and relies only on pre-cached, declared inputs.

---

## Method 3: Verifying Sandboxing

Bazel uses sandboxing to isolate build actions. On supported systems (Linux and macOS), actions are run in a restricted environment where only declared inputs are visible.

1.  **Run a clean build:**
    ```bash
    bazelisk clean && bazelisk build //...
    ```
2.  **Observe the output:**
    During the build, look at the status lines. You should see the sandbox executor being used for the Elm compilation action:
    ```
    [19 / 20] Elm main_js.js; 1s linux-sandbox
    ```
    The `linux-sandbox` (or `darwin-sandbox` on macOS) tag confirms that the Elm compiler was executed inside an isolated container, preventing it from accessing files on your host system that were not explicitly declared as inputs in the `BUILD.bazel` file.
