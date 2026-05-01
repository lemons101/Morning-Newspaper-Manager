import json
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
PROMPTS = ROOT / 'runtime/llm_candidate_prompts.json'
OUT = ROOT / 'runtime/llm_candidate_subagent_batch_plan.json'

payload = json.loads(PROMPTS.read_text(encoding='utf-8'))
items = payload.get('items', []) if isinstance(payload, dict) else []
plan = {
    'count': len(items),
    'items': [
        {
            'item_id': item.get('item_id', ''),
            'title': item.get('title', ''),
            'prompt': item.get('prompt', ''),
            'status': 'pending',
            'result': None,
        }
        for item in items if isinstance(item, dict)
    ]
}
OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote batch plan with {plan["count"]} items to {OUT}')
