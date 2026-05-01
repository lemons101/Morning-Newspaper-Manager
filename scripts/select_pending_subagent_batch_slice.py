import json
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
PLAN = ROOT / 'runtime/llm_candidate_subagent_batch_plan.json'
OUT = ROOT / 'runtime/llm_candidate_subagent_pending_slice.json'
MAX_ITEMS = 5

payload = json.loads(PLAN.read_text(encoding='utf-8'))
items = payload.get('items', []) if isinstance(payload, dict) else []
selected = []
for item in items:
    if not isinstance(item, dict):
        continue
    if str(item.get('status') or '') != 'pending':
        continue
    selected.append(item)
    if len(selected) >= MAX_ITEMS:
        break
out = {'count': len(selected), 'items': selected}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote pending slice with {out["count"]} items to {OUT}')
