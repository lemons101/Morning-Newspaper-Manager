import json
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
PLAN = ROOT / 'runtime/llm_candidate_subagent_batch_plan.json'
TEST = ROOT / 'runtime/llm_candidate_subagent_test_slice.json'
MAX_ITEMS = 3

payload = json.loads(PLAN.read_text(encoding='utf-8'))
items = payload.get('items', []) if isinstance(payload, dict) else []
subset = {
    'count': 0,
    'items': [],
}
for item in items:
    if not isinstance(item, dict):
        continue
    subset['items'].append(item)
    if len(subset['items']) >= MAX_ITEMS:
        break
subset['count'] = len(subset['items'])
TEST.write_text(json.dumps(subset, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote test slice with {subset["count"]} items to {TEST}')
