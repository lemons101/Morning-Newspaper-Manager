#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="${1:-${MORNING_NEWSPAPER_PROJECT_ROOT:-$DEFAULT_ROOT}}"
cd "$PROJECT_ROOT"

python3 src/pipeline/collect.py --project-root "$PROJECT_ROOT"
python3 "$PROJECT_ROOT/scripts/rebuild_dashboard.py" "$PROJECT_ROOT"

echo "[OK] daily newspaper regenerated"
echo "[OK] html: $PROJECT_ROOT/runtime/dashboard.html"
