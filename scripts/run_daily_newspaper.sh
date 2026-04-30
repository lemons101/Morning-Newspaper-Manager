#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/root/projects/Morning-Newspaper-Manager}"
cd "$PROJECT_ROOT"

python3 src/pipeline/collect.py --project-root "$PROJECT_ROOT"

echo "[OK] daily newspaper regenerated"
echo "[OK] html: $PROJECT_ROOT/runtime/dashboard.html"
