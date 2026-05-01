import json
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
RUNTIME = ROOT / 'runtime'
TRIAGE = RUNTIME / 'triage_items.json'
PLAN = RUNTIME / 'llm_candidate_subagent_batch_plan.json'
OUT = RUNTIME / 'triage_items_llm_scored.json'


def fallback_score(item: dict) -> dict:
    priority = str(item.get('priority') or 'FYI').strip()
    source_type = str(item.get('source_type') or '').strip()
    title = str(item.get('title') or '').lower()
    summary = ' '.join([str(item.get('summary') or ''), str(item.get('short_summary') or '')]).lower()
    heat = 3
    if 'score=' in summary or 'comments=' in summary or 'stars=' in summary or 'forks=' in summary:
        heat = 4
    if source_type == 'github_advisory':
        heat = max(heat, 4)
    ai_rel = 3
    if any(k in f'{title} {summary}' for k in ['ai', 'agent', 'llm', 'model', 'mcp', 'multimodal', 'inference', 'benchmark']):
        ai_rel = 5
    elif source_type in {'github_advisory', 'github_high_stars', 'hackernews_top'}:
        ai_rel = 4
    quality = 3
    if len(str(item.get('summary') or '')) > 160:
        quality = 4
    keep = 'yes' if priority in {'Urgent', 'Important'} or ai_rel >= 4 else 'no'
    candidate = 8 if priority == 'Urgent' else 6 if priority == 'Important' else 4
    if keep == 'no':
        candidate = min(candidate, 4)
    return {
        'priority_llm': priority if priority in {'Urgent', 'Important', 'FYI'} else 'FYI',
        'candidate_score': candidate,
        'quality_score': quality,
        'ai_relevance_score': ai_rel,
        'heat_score': heat,
        'final_keep': keep,
        'editorial_reason': 'LLM 结果缺失，回退到规则与来源信号综合判断。',
        'llm_candidate_method': 'fallback',
    }


triage_payload = json.loads(TRIAGE.read_text(encoding='utf-8'))
triage_items = triage_payload.get('items', []) if isinstance(triage_payload, dict) else []
plan_payload = json.loads(PLAN.read_text(encoding='utf-8'))
plan_items = plan_payload.get('items', []) if isinstance(plan_payload, dict) else []
plan_map = {
    str(item.get('item_id') or ''): item
    for item in plan_items
    if isinstance(item, dict)
}
merged = []
for item in triage_items:
    if not isinstance(item, dict):
        continue
    if str(item.get('channel') or '') == 'mail_alert':
        row = dict(item)
        row.update({
            'priority_llm': 'FYI',
            'candidate_score': 0,
            'quality_score': 0,
            'ai_relevance_score': 0,
            'heat_score': 0,
            'final_keep': 'no',
            'editorial_reason': '邮件事务不参与新闻候选池粗筛。',
            'llm_candidate_method': 'skip_mail_alert',
        })
        merged.append(row)
        continue
    entry = plan_map.get(str(item.get('item_id') or ''))
    row = dict(item)
    result = entry.get('result') if isinstance(entry, dict) else None
    if isinstance(result, dict):
        row.update(result)
        row['llm_candidate_method'] = 'subagent'
    else:
        row.update(fallback_score(item))
    merged.append(row)

payload = {
    'selection_method': 'llm_candidate_subagent_merge_v1',
    'count': len(merged),
    'items': merged,
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote merged scored items: {len(merged)} -> {OUT}')
