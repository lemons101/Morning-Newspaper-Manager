from __future__ import annotations

import json
from pathlib import Path
import sys

from _project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(sys.argv[1] if len(sys.argv) > 1 else None)
RUNTIME = PROJECT_ROOT / 'runtime'
EXPERIMENT = PROJECT_ROOT / 'runtime_experiments' / 'display_rewrite' / 'display_rewrite_input.json'


def _load_experiment_items() -> list[dict]:
    payload = json.loads(EXPERIMENT.read_text(encoding='utf-8'))
    items = payload.get('items', []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _to_runtime_item(item: dict) -> dict:
    rank = item.get('rank')
    title = str(item.get('title') or '').strip()
    title_zh = str(item.get('title_zh') or title).strip()
    summary = str(item.get('summary_main') or item.get('why_it_matters') or '').strip()
    why = str(item.get('why_it_matters') or '').strip()
    return {
        'rank': rank,
        'item_id': f'display-rewrite:{rank}',
        'title': title,
        'title_en': title,
        'title_zh': title_zh,
        'source_name': str(item.get('source_name') or '').strip(),
        'source_type': str(item.get('source_type') or '').strip(),
        'priority': 'Important',
        'url': str(item.get('url') or '').strip(),
        'published_at': str(item.get('published_at') or '').strip(),
        'summary_zh': summary,
        'summary_main': summary,
        'why_it_matters': why,
        'body_source': 'display_rewrite_promoted',
        'body_fetch_status': 'rewritten',
        'body_quality': 'good',
        'body_length': len(summary),
        'body_text': item.get('body_text'),
        'content_basis': 'display_rewrite',
        'editorial_focus': '',
        'editorial_angle': '',
        'editorial_summary_hint': summary,
        'editorial_priority': 'headline_candidate' if isinstance(rank, int) and rank <= 3 else 'supporting_signal',
        'card_title': title_zh,
        'card_summary': summary,
        'key_points': item.get('key_points') or [],
    }


def _build_final_payload(items: list[dict]) -> dict:
    headline = '今日 AI 早报'
    lead = ' | '.join([str(item.get('summary_main') or '').strip() for item in items[:3] if str(item.get('summary_main') or '').strip()])
    return {
        'generated_at': None,
        'headline': headline,
        'lead': lead,
        'count': len(items),
        'source_count': len(items),
        'items_used': [str(item.get('item_id') or '') for item in items],
        'generation_mode': 'display_rewrite_promoted',
        'items': items,
    }


def main() -> int:
    items = [_to_runtime_item(item) for item in _load_experiment_items()]
    editorial_payload = {
        'generated_at': None,
        'count': len(items),
        'source_mode': 'display_rewrite_formal',
        'items': items,
    }
    (RUNTIME / 'top10_editorial_ready.json').write_text(json.dumps(editorial_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (RUNTIME / 'final_newspaper.json').write_text(json.dumps(_build_final_payload(items), ensure_ascii=False, indent=2), encoding='utf-8')
    print(RUNTIME / 'top10_editorial_ready.json')
    print(RUNTIME / 'final_newspaper.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
