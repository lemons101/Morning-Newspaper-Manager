from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROMPT_PATH = ROOT / 'references' / 'display_rewrite_prompt.md'
RUNTIME = ROOT / 'runtime'
EXPERIMENT_DIR = ROOT / 'runtime_experiments' / 'display_rewrite'


def _load_items() -> list[dict]:
    payload = json.loads((RUNTIME / 'top10_editorial_ready.json').read_text(encoding='utf-8'))
    items = payload.get('items', []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _build_input_packet(items: list[dict]) -> dict:
    packet = {
        'instruction': 'Use references/display_rewrite_prompt.md to rewrite these items into display-ready Chinese copy.',
        'prompt_path': str(PROMPT_PATH),
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
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    items = _load_items()
    packet = _build_input_packet(items)
    out = EXPERIMENT_DIR / 'display_rewrite_input.json'
    out.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    print(out)
    print('next_step: use references/display_rewrite_prompt.md + this JSON with your chosen model, then write results to runtime_experiments/display_rewrite/display_rewrite_output.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
