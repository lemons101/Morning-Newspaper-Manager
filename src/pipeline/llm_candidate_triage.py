from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

MAX_ITEMS = 40


def run_llm_candidate_triage(root: Path) -> Path:
    runtime = root / 'runtime'
    triaged = _read_items(runtime / 'triage_items.json')
    prompts_payload = {
        'generated_at': _now_iso(),
        'count': 0,
        'items': [],
    }
    plan_payload = {
        'generated_at': _now_iso(),
        'count': 0,
        'items': [],
    }
    scored: List[Dict[str, Any]] = []
    subagent_hits = 0
    fallback_hits = 0

    for item in triaged[:MAX_ITEMS]:
        row = dict(item)
        if str(item.get('channel') or '') == 'mail_alert':
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
            scored.append(row)
            continue

        prompt = _build_llm_prompt(item)
        prompt_row = {
            'item_id': item.get('item_id', ''),
            'title': item.get('title', ''),
            'prompt': prompt,
        }
        prompts_payload['items'].append(prompt_row)
        plan_payload['items'].append({
            'item_id': item.get('item_id', ''),
            'title': item.get('title', ''),
            'prompt': prompt,
            'status': 'pending',
            'result': None,
        })

        result = _extract_existing_subagent_result(runtime / 'llm_candidate_subagent_batch_plan.json', str(item.get('item_id') or ''))
        if isinstance(result, dict):
            row.update(result)
            row['llm_candidate_method'] = 'subagent'
            subagent_hits += 1
        else:
            row.update(_fallback_score_item(item))
            fallback_hits += 1
        scored.append(row)

    prompts_payload['count'] = len(prompts_payload['items'])
    plan_payload['count'] = len(plan_payload['items'])
    (runtime / 'llm_candidate_prompts.json').write_text(json.dumps(prompts_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (runtime / 'llm_candidate_subagent_batch_plan.json').write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding='utf-8')

    payload = {
        'generated_at': _now_iso(),
        'selection_method': 'llm_candidate_triage_v2_subagent_ready',
        'count': len(scored),
        'subagent_hits': subagent_hits,
        'fallback_hits': fallback_hits,
        'items': scored,
    }
    out = runtime / 'triage_items_llm_scored.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def select_triage_candidates_by_llm(items: List[Dict[str, Any]], *, limit: int = 15) -> List[Dict[str, Any]]:
    news_items = [item for item in items if str(item.get('channel') or '') != 'mail_alert']
    ranked = sorted(news_items, key=_rank_key, reverse=True)

    fresh_48h = [item for item in ranked if _hours_since_published(item) is not None and _hours_since_published(item) <= 48]
    fallback_recent = [item for item in ranked if item not in fresh_48h and _hours_since_published(item) is not None and _hours_since_published(item) <= 96]
    unresolved_time = [item for item in ranked if item not in fresh_48h and item not in fallback_recent and _hours_since_published(item) is None]
    stale = [item for item in ranked if item not in fresh_48h and item not in fallback_recent and item not in unresolved_time]

    selected = (fresh_48h + fallback_recent + unresolved_time + stale)[:max(1, limit)]
    rows = []
    for idx, item in enumerate(selected, 1):
        row = dict(item)
        row['candidate_rank'] = idx
        age_hours = _hours_since_published(item)
        row['age_hours'] = age_hours
        rows.append(row)
    return rows


def _read_items(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    items = payload.get('items', [])
    return [item for item in items if isinstance(item, dict)]


def _extract_existing_subagent_result(plan_path: Path, item_id: str) -> Dict[str, Any] | None:
    if not item_id or not plan_path.exists():
        return None
    try:
        payload = json.loads(plan_path.read_text(encoding='utf-8'))
    except Exception:
        return None
    items = payload.get('items', []) if isinstance(payload, dict) else []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get('item_id') or '') != item_id:
            continue
        result = item.get('result')
        if isinstance(result, dict):
            return _normalize_result(result)
    return None


def _normalize_result(data: Dict[str, Any]) -> Dict[str, Any]:
    priority = str(data.get('priority_llm') or '').strip()
    if priority not in {'Urgent', 'Important', 'FYI'}:
        priority = 'FYI'
    final_keep = str(data.get('final_keep') or '').strip().lower()
    if final_keep not in {'yes', 'no'}:
        final_keep = 'yes' if priority in {'Urgent', 'Important'} else 'no'
    return {
        'priority_llm': priority,
        'candidate_score': _clamp_int(data.get('candidate_score'), 1, 10),
        'quality_score': _clamp_int(data.get('quality_score'), 1, 10),
        'ai_relevance_score': _clamp_int(data.get('ai_relevance_score'), 1, 10),
        'heat_score': _clamp_int(data.get('heat_score'), 1, 10),
        'final_keep': final_keep,
        'editorial_reason': _trim(str(data.get('editorial_reason') or ''), 160),
    }


def _build_llm_prompt(item: Dict[str, Any]) -> str:
    title = _trim(str(item.get('title') or ''), 200)
    source_name = _trim(str(item.get('source_name') or ''), 80)
    source_type = _trim(str(item.get('source_type') or ''), 80)
    url = _trim(str(item.get('url') or ''), 200)
    published_at = _trim(str(item.get('published_at') or ''), 64)
    summary = _trim(str(item.get('summary') or item.get('short_summary') or ''), 360)
    heat = _infer_heat_signal(item)
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


def _infer_heat_signal(item: Dict[str, Any]) -> str:
    parts = []
    source_type = str(item.get('source_type') or '').strip()
    summary = str(item.get('summary') or item.get('short_summary') or '').strip()
    if source_type:
        parts.append(f'来源={source_type}')
    if 'score=' in summary or 'comments=' in summary or 'stars=' in summary or 'forks=' in summary or 'severity=' in summary:
        parts.append(summary)
    else:
        parts.append(str(item.get('title') or '').strip())
    return _trim(' | '.join(x for x in parts if x), 160)


def _fallback_score_item(item: Dict[str, Any]) -> Dict[str, Any]:
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
    elif source_type in {'github_advisory', 'github_high_stars', 'hackernews_top', 'tavily_skill'}:
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


def _rank_key(item: Dict[str, Any]) -> tuple:
    keep_rank = 1 if str(item.get('final_keep') or '') == 'yes' else 0
    priority = str(item.get('priority_llm') or 'FYI')
    priority_rank = {'Urgent': 3, 'Important': 2, 'FYI': 1}.get(priority, 0)
    freshness_rank = _freshness_rank(item)
    topical_penalty = _topic_penalty(item)
    time_penalty = _time_confidence_penalty(item)
    return (
        keep_rank,
        freshness_rank,
        priority_rank,
        topical_penalty,
        time_penalty,
        int(item.get('candidate_score') or 0),
        int(item.get('heat_score') or 0),
        int(item.get('quality_score') or 0),
        int(item.get('ai_relevance_score') or 0),
        float(item.get('impact_score') or 0),
        float(item.get('confidence') or 0),
        str(item.get('published_at') or ''),
    )


def _hours_since_published(item: Dict[str, Any]) -> float | None:
    raw = str(item.get('published_at') or '').strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt.astimezone(timezone.utc)).total_seconds() / 3600)


def _freshness_rank(item: Dict[str, Any]) -> int:
    hours = _hours_since_published(item)
    if hours is None:
        return 0 if str(item.get('source_type') or '').strip() in {'tavily_skill', 'tavily_search'} else 1
    if hours <= 24:
        return 4
    if hours <= 48:
        return 3
    if hours <= 96:
        return 2
    return 1


def _time_confidence_penalty(item: Dict[str, Any]) -> int:
    source_type = str(item.get('source_type') or '').strip()
    hours = _hours_since_published(item)
    if hours is None and source_type in {'tavily_skill', 'tavily_search'}:
        return -2
    return 0


def _topic_penalty(item: Dict[str, Any]) -> int:
    title = str(item.get('title') or '').lower()
    url = str(item.get('url') or '').lower()
    penalty = 0
    if 'this month' in title or 'monthly' in title or 'newsletter' in title:
        penalty -= 2
    if '/2026/04/' in url or '2026-04-30' in url:
        penalty -= 1
    return penalty


def _clamp_int(value: Any, low: int, high: int) -> int:
    try:
        iv = int(value)
    except Exception:
        iv = low
    return max(low, min(high, iv))


def _trim(text: str, max_chars: int) -> str:
    clean = re.sub(r'\s+', ' ', text or '').strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + '...'


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
