#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
RUNTIME_HTML="$PROJECT_ROOT/runtime/dashboard.html"
URL="${2:-}"

if [[ ! -f "$RUNTIME_HTML" ]]; then
  echo "[MISSING] $RUNTIME_HTML"
  exit 1
fi

echo "[LOCAL] $RUNTIME_HTML"
stat "$RUNTIME_HTML"

if [[ -n "$URL" ]]; then
  echo
  echo "[REMOTE] $URL"
  curl -I --max-time 10 "$URL"
else
  echo
  echo "[INFO] No remote URL provided; local freshness only."
fi
