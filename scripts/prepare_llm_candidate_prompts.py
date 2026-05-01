import json
from pathlib import Path

ROOT = Path('/root/projects/Morning-Newspaper-Manager')
RUNTIME = ROOT / 'runtime'
SRC = RUNTIME / 'triage_items.json'
OUT = RUNTIME / 'llm_candidate_prompts.json'
MAX_ITEMS = 20


def trim(text: str, limit: int) -> str:
    text = ' '.join((text or '').split()).strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + '...'


def infer_heat_signal(item: dict) -> str:
    parts = []
    source_type = str(item.get('source_type') or '').strip()
    summary = str(item.get('summary') or item.get('short_summary') or '').strip()
    if source_type:
        parts.append(f'来源={source_type}')
    if 'score=' in summary or 'comments=' in summary or 'stars=' in summary or 'forks=' in summary or 'severity=' in summary:
        parts.append(summary)
    else:
        parts.append(str(item.get('title') or '').strip())
    return trim(' | '.join(x for x in parts if x), 160)


def build_prompt(item: dict) -> str:
    title = trim(str(item.get('title') or ''), 200)
    source_name = trim(str(item.get('source_name') or ''), 80)
    source_type = trim(str(item.get('source_type') or ''), 80)
    url = trim(str(item.get('url') or ''), 200)
    published_at = trim(str(item.get('published_at') or ''), 64)
    summary = trim(str(item.get('summary') or item.get('short_summary') or ''), 360)
    heat = infer_heat_signal(item)
    return (
        '你是 AI 晨报编辑，正在做“15 条候选池”的粗筛。\n\n'
        '请基于下面材料，判断这条内容是否值得进入今天 AI 晨报的候选池。\n'
        '请综合考虑：\n'
        '1. AI 主线相关性（模型、Agent、开源工具、AI 商业化、企业采用、AI 安全、监管）。\n'
        '2. 新闻价值和信息密度。\n'
        '3. 热度/传播势能（如 HN 分数、评论、GitHub stars、官方公告、漏洞严重度等）。\n'
        '4. 时效性。\n'
        '5. 是否值得进入今天的前 15 条候选池。\n\n'
        '仅输出 JSON，不要输出解释。\n'
        'JSON 格式：\n'
        '{"priority_llm":"Urgent|Important|FYI","candidate_score":1,"quality_score":1,"ai_relevance_score":1,"heat_score":1,"final_keep":"yes|no","editorial_reason":"..."}\n\n'
        f'标题: {title}\n'
        f'来源名称: {source_name}\n'
        f'来源类型: {source_type}\n'
        f'链接: {url}\n'
        f'发布时间: {published_at}\n'
        f'热度/传播信号: {heat}\n'
        f'摘要: {summary}\n'
    )


payload = json.loads(SRC.read_text(encoding='utf-8'))
items = payload.get('items', []) if isinstance(payload, dict) else []
out = {'count': 0, 'items': []}
for item in items:
    if not isinstance(item, dict):
        continue
    if str(item.get('channel') or '') == 'mail_alert':
        continue
    out['items'].append({
        'item_id': item.get('item_id', ''),
        'title': item.get('title', ''),
        'prompt': build_prompt(item),
    })
    if len(out['items']) >= MAX_ITEMS:
        break
out['count'] = len(out['items'])
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'wrote {out["count"]} prompts to {OUT}')
