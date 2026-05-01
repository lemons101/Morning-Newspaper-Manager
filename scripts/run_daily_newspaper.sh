#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/root/projects/Morning-Newspaper-Manager}"
cd "$PROJECT_ROOT"

python3 src/pipeline/collect.py --project-root "$PROJECT_ROOT"

python3 - <<'PY'
from pathlib import Path
from src.dashboard.static_html import write_static_dashboard

root = Path('/root/projects/Morning-Newspaper-Manager')
runtime = root / 'runtime'
out = runtime / 'dashboard.html'
write_static_dashboard(runtime, out)
print(f"[OK] static html regenerated: {out}")
PY

echo "[OK] daily newspaper regenerated"
echo "[OK] html: $PROJECT_ROOT/runtime/dashboard.html"
