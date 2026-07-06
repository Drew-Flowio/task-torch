#!/usr/bin/env bash
# Convenience wrapper — runs the XTTS setup from the insight_ios folder.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
exec bash "$SCRIPT_DIR/tools/xtts/setup_mac.sh" "$@"
