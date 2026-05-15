from __future__ import annotations

import json
from pathlib import Path
import sys

from _project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(sys.argv[1] if len(sys.argv) > 1 else None)
PROMPT_PATH = PROJECT_ROOT / 'references' / 'display_rewrite_prompt.md'
RUNTIME = PROJECT_ROOT / 'runtime'
OUT_DIR = PROJECT_ROOT / 'runtime_experiments' / 'display_rewrite'


def _load_items() -> list[dict]:
    payload = json.loads((RUNTIME / 'top10_editorial_ready_base.json').read_text(encoding='utf-8'))
    items = payload.get('items', []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _build_packet(items: list[dict]) -> dict:
    packet = {
        'instruction': 'Use references/display_rewrite_prompt.md to rewrite these items into display-ready Chinese copy.',
        'prompt_path': str(PROMPT_PATH),
        'mode': 'formal_publish_layer',
        'items': [],
    }
    for item in items:
        packet['items'].append({
            'rank': item.get('rank'),
            'title': item.get('title'),
            'title_zh': item.get('title_zh'),
            'source_name': item.get('source_name'),
            'source_type': item.get('source_type'),
            'url': item.get('url'),
            'summary_main': item.get('summary_main'),
            'why_it_matters': item.get('why_it_matters'),
            'key_points': item.get('key_points') or [],
            'body_text': item.get('body_text'),
        })
    return packet


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / 'display_rewrite_input.json'
    out.write_text(json.dumps(_build_packet(_load_items()), ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)
    print('display publish input prepared')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
