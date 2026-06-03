#!/usr/bin/env python3
import sys
from pathlib import Path

# Calculate paths relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
GENERATED_PYTHON_DIR = SCRIPT_DIR / 'build' / 'generated_python' / 'python'

# Ensure the generated python protos are importable
if GENERATED_PYTHON_DIR.exists():
    sys.path.append(str(GENERATED_PYTHON_DIR))
else:
    print(f"Error: Generated python directory not found at {GENERATED_PYTHON_DIR}")
    print("Please build the project first (./build.sh)")
    sys.exit(1)

try:
    import ping_pb2
except ImportError as e:
    print(f"Error: Failed to import ping_pb2: {e}")
    print("Ensure you have built the project.")
    sys.exit(1)

try:
    import pw_system.console
except ImportError:
    print("Error: Failed to import pw_system.console.")
    print("Please run this script from a Pigweed bootstrapped environment:")
    print("  cd path/to/pigweed")
    print("  . ./bootstrap.sh")
    print("  python path/to/this/project/run_console.py --socket-addr default")
    sys.exit(1)

def main():
    # If no connection arguments are provided, default to socket
    if not any(arg in sys.argv for arg in ['-s', '--socket-addr', '-d', '--device']):
        sys.argv.extend(['--socket-addr', 'default'])
        print("Defaulting to --socket-addr default")

    # Force --no-rpc-logging since the demo server doesn't support RPC logging
    if '--rpc-logging' in sys.argv:
        print("Warning: RPC logging is not supported by this demo server. Forcing --no-rpc-logging.")
        sys.argv.remove('--rpc-logging')
    if '--no-rpc-logging' not in sys.argv:
        sys.argv.append('--no-rpc-logging')

    # Pass our compiled proto to the console
    sys.exit(pw_system.console.main(compiled_protos=[ping_pb2]))



if __name__ == '__main__':
    main()
