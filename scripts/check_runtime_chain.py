from __future__ import annotations

import json
import sys
from pathlib import Path

from _project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(sys.argv[1] if len(sys.argv) > 1 else None)
RUNTIME = PROJECT_ROOT / 'runtime'

CHECKS = [
    ('top10_items', RUNTIME / 'top10_items.json'),
    ('top10_enriched_items', RUNTIME / 'top10_enriched_items.json'),
    ('top10_editorial_ready', RUNTIME / 'top10_editorial_ready.json'),
    ('final_newspaper', RUNTIME / 'final_newspaper.json'),
    ('dashboard', RUNTIME / 'dashboard.html'),
]


def _json_count(path: Path) -> str:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return f'json-error:{exc.__class__.__name__}'
    if isinstance(data, list):
        return str(len(data))
    if isinstance(data, dict):
        for key in ('top10', 'top_items', 'items', 'lead'):
            value = data.get(key)
            if isinstance(value, list):
                return f'{len(value)} via {key}'
        return f'dict:{len(data)} keys'
    return type(data).__name__


def main() -> int:
    ok = True
    print('runtime chain check')
    print(f'project_root={PROJECT_ROOT}')
    for name, path in CHECKS:
        if not path.exists():
            ok = False
            print(f'[MISSING] {name}: {path}')
            continue
        size = path.stat().st_size
        if path.suffix == '.json':
            detail = _json_count(path)
            print(f'[OK] {name}: {path} size={size} count={detail}')
        else:
            print(f'[OK] {name}: {path} size={size}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
