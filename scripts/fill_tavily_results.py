import json, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
plan = json.loads((ROOT / 'runtime/tavily_search_plan.json').read_text(encoding='utf-8'))
out = {
    'generated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
    'source': 'openclaw_tavily',
    'items': [],
}
seen = set()
script = '/root/.openclaw/workspace/skills/openclaw-tavily-search/scripts/tavily_search.py'
for item in plan.get('items', []):
    q = item.get('query')
    if not q:
        continue
    max_items = min(int(item.get('max_items') or 5), 5)
    cmd = ['python3', script, '--query', q, '--max-results', str(max_items), '--format', 'brave']
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        continue
    try:
        obj = json.loads(p.stdout)
    except Exception:
        continue
    for r in obj.get('results', []):
        if not isinstance(r, dict):
            continue
        url = str(r.get('url') or '').strip()
        title = str(r.get('title') or '').strip()
        snippet = str(r.get('snippet') or '').strip()
        if not url or not title or url in seen:
            continue
        seen.add(url)
        out['items'].append({
            'topic_id': item.get('topic_id'),
            'topic_name': item.get('topic_name'),
            'title': title,
            'url': url,
            'summary': snippet,
            'source_name': 'Tavily Search',
            'published_at': '',
            'fetched_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            'is_recent': True,
            'relevance_note': item.get('topic_name') or 'Tavily 搜索结果',
            'source_type': 'tavily_skill',
            'channel': 'openclaw_tavily',
        })
(ROOT / 'runtime/tavily_search_results.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print('wrote', len(out['items']), 'items')
