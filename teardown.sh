#!/usr/bin/env bash
# teardown.sh — Linux/macOS convenience wrapper over teardown.py. Usage: ./teardown.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec sudo "$(command -v python3)" teardown.py "$@"
