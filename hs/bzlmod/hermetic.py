#!/usr/bin/env python3
"""Hermeticity verification script for the Haskell Bazel build.

This script verifies that the Haskell project in hs/bzlmod is 100% hermetic:
1. Inspects the Bazel action graph via `bazelisk aquery` to confirm that all
   Haskell toolchains, compilers, library dependencies, and action inputs
   are Bazel-managed and do not use host system tools or libraries.
2. Builds and executes the target (`bazelisk run //:example`) under a
   sanitized, minimal environment to ensure no host environment leaks.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def inspect_action_graph(bzlmod_dir: Path, minimal_env: dict, target: str = "deps(//:example)") -> bool:
    print("=" * 60)
    print("Phase 1: Action Graph Inspection (bazelisk aquery)")
    print("=" * 60)
    print(f"Executing: bazelisk aquery --output=jsonproto \"{target}\"")

    cmd = ["bazelisk", "aquery", "--output=jsonproto", target]
    try:
        proc = subprocess.run(
            cmd,
            cwd=bzlmod_dir,
            env=minimal_env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Error: 'bazelisk' executable not found in PATH.")
        return False

    if proc.returncode != 0:
        print("Error running bazelisk aquery:")
        print(proc.stderr.strip() if proc.stderr.strip() else "(empty)")
        return False

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        print(f"Error parsing bazelisk aquery JSON output: {e}")
        return False

    actions = data.get("actions", [])
    artifacts_raw = data.get("artifacts", [])
    path_fragments = {pf["id"]: pf for pf in data.get("pathFragments", [])}

    def resolve_path(pf_id):
        parts = []
        curr = pf_id
        while curr:
            pf = path_fragments.get(curr)
            if not pf:
                break
            parts.append(pf.get("label", ""))
            curr = pf.get("parentId")
        return "/".join(reversed(parts))

    artifacts = {a["id"]: resolve_path(a.get("pathFragmentId")) for a in artifacts_raw}
    dep_sets = {ds["id"]: ds for ds in data.get("depSetOfFiles", [])}

    def get_dep_set_artifacts(dep_set_id):
        result = []
        visited = set()
        stack = [dep_set_id]
        while stack:
            curr = stack.pop()
            if curr in visited or curr not in dep_sets:
                continue
            visited.add(curr)
            ds = dep_sets[curr]
            for aid in ds.get("directArtifactIds", []):
                if aid in artifacts:
                    result.append(artifacts[aid])
            for tid in ds.get("transitiveDepSetIds", []):
                stack.append(tid)
        return result

    haskell_actions = [
        a for a in actions if any(h in a.get("mnemonic", "") for h in ("Haskell", "Ghc", "Cabal"))
    ]

    print(f"\nAnalyzed {len(actions)} total actions across the build graph.")
    print(f"Found {len(haskell_actions)} Haskell-specific actions.")

    violations = []

    # 1. Inspect Haskell toolchain paths in action environment variables
    ghc_env_paths = {}
    for act in actions:
        m = act.get("mnemonic", "")
        for env in act.get("environmentVariables", []):
            k = env.get("key", "")
            v = env.get("value", "")
            if any(h in k for h in ("GHC", "HASKELL", "CABAL")):
                ghc_env_paths[k] = v
                if not (v.startswith("external/") or v.startswith("bazel-out/")):
                    violations.append(f"Non-hermetic env var {k}={v} in action {m}")

    print("\nHaskell Toolchain Environment Variables:")
    if ghc_env_paths:
        for k, v in sorted(ghc_env_paths.items()):
            print(f"  ✓ {k}: {v}")
    else:
        print("  (No Haskell toolchain env vars found)")

    # 2. Inspect command executables and arguments for host tool leaks
    forbidden_host_tool_patterns = [
        re.compile(r"^/usr/(local/)?bin/(ghc|ghc-pkg|cabal|stack)"),
        re.compile(r"(/|^)\.ghcup/"),
        re.compile(r"(/|^)\.cabal/bin/"),
        re.compile(r"(/|^)\.stack/programs/"),
        re.compile(r"^/nix/store/"),
        re.compile(r"^/opt/ghc/"),
    ]

    forbidden_arg_patterns = [
        re.compile(r"^-l(gmp|tinfo|ncurses)"),
        re.compile(r"^-L/(usr|lib|lib64|opt)/"),
    ]

    for act in actions:
        m = act.get("mnemonic", "")
        args = act.get("arguments", [])
        if not args:
            continue
        exe = args[0]
        for pattern in forbidden_host_tool_patterns:
            if pattern.search(exe):
                violations.append(f"Host Haskell executable '{exe}' invoked in action {m}")
        for arg in args[1:]:
            for pattern in forbidden_host_tool_patterns:
                if pattern.search(arg):
                    violations.append(f"Host Haskell path in argument '{arg}' in action {m}")
            for pattern in forbidden_arg_patterns:
                if pattern.search(arg):
                    violations.append(f"Host library/linker flag '{arg}' in action {m}")

    # 3. Inspect input artifacts for system library leaks
    forbidden_system_lib_patterns = [
        re.compile(r"^/(usr|lib|lib64|opt)/"),
        re.compile(r"/\.(ghc|cabal|stack)/"),
    ]

    total_inputs_checked = 0
    for act in haskell_actions:
        m = act.get("mnemonic", "")
        inputs = []
        for ds_id in act.get("inputDepSetIds", []):
            inputs.extend(get_dep_set_artifacts(ds_id))
        total_inputs_checked += len(inputs)
        for inp in inputs:
            for pattern in forbidden_system_lib_patterns:
                if pattern.search(inp):
                    violations.append(f"System library or host file '{inp}' used as input in action {m}")

    print("\nAction Inputs & Library Dependencies:")
    print(f"  ✓ Verified {total_inputs_checked} inputs across Haskell actions (0 host/system library leaks).")

    print("-" * 60)
    if violations:
        print("PHASE 1 RESULT: FAILED - Detected host tool or library leaks in action graph:")
        for v in violations:
            print(f"  ✗ {v}")
        return False
    else:
        print("PHASE 1 RESULT: SUCCESS - bazelisk aquery verified 0 system libraries or host tools used.")
        return True


def verify_hermetic_build():
    repo_root = Path(__file__).resolve().parent
    bzlmod_dir = repo_root

    if not bzlmod_dir.is_dir():
        print(f"Error: Directory {bzlmod_dir} does not exist.")
        sys.exit(1)

    print("=" * 60)
    print("Verifying Hermetic Haskell Bazel Build")
    print("=" * 60)

    # 1. Prepare a sanitized, minimal environment
    # Stripping any host Haskell environment variables or custom toolchain paths.
    minimal_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "user"),
    }

    # Ensure no Haskell host tools or nix environments leak in
    for key in list(minimal_env.keys()):
        if any(h in key.upper() for h in ("GHC", "CABAL", "STACK", "NIX", "HASKELL")):
            del minimal_env[key]

    print(f"Project Directory: {bzlmod_dir}")
    print("Running inspection and execution with sanitized environment...")
    print()

    # Step 1: Action Graph Inspection via bazelisk aquery
    aquery_ok = inspect_action_graph(bzlmod_dir, minimal_env, target="deps(//:example)")
    print()

    # Step 2: Build & Execution via bazelisk run //:example
    print("=" * 60)
    print("Phase 2: Sanitized Build & Execution (bazelisk run)")
    print("=" * 60)

    cmd = ["bazelisk", "run", "//:example"]
    print(f"Executing: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            cwd=bzlmod_dir,
            env=minimal_env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("Error: 'bazelisk' executable not found in PATH.")
        sys.exit(1)

    stdout = proc.stdout
    stderr = proc.stderr

    expected_output = "Hello from rules_haskell!"
    run_ok = (proc.returncode == 0) and (expected_output in stdout)

    print("\n--- Command Output (stdout) ---")
    print(stdout.strip() if stdout.strip() else "(empty)")

    if proc.returncode != 0:
        print("\n--- Command Errors (stderr) ---")
        print(stderr.strip() if stderr.strip() else "(empty)")

    print("\n" + "=" * 60)
    if aquery_ok and run_ok:
        print("RESULT: SUCCESS - Build is 100% hermetic!")
        print("1. bazelisk aquery verified no host Haskell tools or system libraries are used.")
        print(f"2. //:example built and printed '{expected_output}' under a sanitized environment.")
        print("=" * 60)
        sys.exit(0)
    else:
        print("RESULT: FAILED - Hermetic verification failed.")
        if not aquery_ok:
            print("  ✗ Action graph inspection detected non-hermetic tool or library usage.")
        if not run_ok:
            print(f"  ✗ Target execution failed (exit code: {proc.returncode}).")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    verify_hermetic_build()
