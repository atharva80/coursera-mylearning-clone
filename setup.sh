#!/usr/bin/env bash
# setup.sh — Linux/macOS convenience wrapper. The real work is in setup.py
# (cross-platform). Usage:  ./setup.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec sudo "$(command -v python3)" setup.py "$@"
