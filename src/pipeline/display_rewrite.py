from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List


LLM_MODEL = os.environ.get('DISPLAY_REWRITE_MODEL', 'hotai/gpt-5.4')
LLM_TIMEOUT_SECONDS = int(os.environ.get('DISPLAY_REWRITE_TIMEOUT_SECONDS', '60'))
BODY_LIMIT = int(os.environ.get('DISPLAY_REWRITE_BODY_LIMIT', '5200'))


class DisplayRewriteError(RuntimeError):
    pass


def run_display_rewrite(root: Path) -> Path:
    runtime = root / 'runtime'
    base_path = runtime / 'top10_editorial_ready_base.json'
    prompt_path = root / 'references' / 'display_rewrite_prompt.md'
    payload = _read_json(base_path)
    prompt_template = prompt_path.read_text(encoding='utf-8')

    items = payload.get('items', []) if isinstance(payload, dict) else []
    source_items = [item for item in items if isinstance(item, dict)]
    rewritten = [_rewrite_item_with_llm(item, prompt_template, index) for index, item in enumerate(source_items, 1)]
    problems = _quality_problems(rewritten)
    if problems:
        raise DisplayRewriteError('display_rewrite quality gate failed:\n' + '\n'.join(f'- {p}' for p in problems))

    out = runtime / 'top10_editorial_ready.json'
    editorial_payload = {
        'generated_at': payload.get('generated_at'),
        'count': len(rewritten),
        'source_mode': 'display_rewrite_llm',
        'model': LLM_MODEL,
        'items': rewritten,
    }
    final_payload = _build_final_payload(payload.get('generated_at'), rewritten)
    out.write_text(json.dumps(editorial_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    (runtime / 'final_newspaper.json').write_text(json.dumps(final_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def _rewrite_item_with_llm(item: Dict[str, Any], prompt_template: str, index: int) -> Dict[str, Any]:
    prompt = _build_prompt(prompt_template, item, index)
    result = _run_llm(prompt)
    normalized = _normalize_llm_result(result, item, index)
    out = dict(item)
    out['rank'] = item.get('rank') or index
    out['card_title'] = normalized['display_title']
    out['title_zh'] = normalized['display_title']
    out['summary_main'] = normalized['display_summary']
    out['summary_zh'] = normalized['display_summary']
    out['card_summary'] = normalized['display_summary']
    out['editorial_summary_hint'] = normalized['display_summary']
    out['key_points'] = normalized['display_points']
    out['display_rewrite_model'] = LLM_MODEL
    out['display_rewrite_method'] = 'llm_prompt'
    out['body_source'] = 'display_rewrite_llm'
    out['content_basis'] = 'display_rewrite_llm'
    return out


def _build_prompt(prompt_template: str, item: Dict[str, Any], index: int) -> str:
    summary_untrusted = _drop_untrusted_copy_if_dirty(item, str(item.get('summary_main') or ''))
    why_untrusted = _drop_untrusted_copy_if_dirty(item, str(item.get('why_it_matters') or ''))
    key_points_untrusted = []
    for point in item.get('key_points') or []:
        clean_point = _drop_untrusted_copy_if_dirty(item, str(point or ''))
        if clean_point:
            key_points_untrusted.append(clean_point)
    packet = {
        'rank': item.get('rank') or index,
        'item_id': item.get('item_id', ''),
        'title': item.get('title', ''),
        'title_zh': item.get('title_zh', ''),
        'source_name': item.get('source_name', ''),
        'source_type': item.get('source_type', ''),
        'url': item.get('url', ''),
        'published_at': item.get('published_at', ''),
        'summary_main_existing_untrusted': summary_untrusted,
        'why_it_matters_existing_untrusted': why_untrusted,
        'key_points_existing_untrusted': key_points_untrusted,
        'summary_basis': item.get('summary_basis', ''),
        'summary_warnings': item.get('summary_warnings') or [],
        'body_fetch_status': item.get('body_fetch_status', ''),
        'body_quality': item.get('body_quality', ''),
        'body_text': _clean_for_prompt(str(item.get('body_text_clean') or item.get('body_text') or ''))[:BODY_LIMIT],
    }
    return (
        f'{prompt_template.strip()}\n\n'
        '## 本次任务补充约束\n\n'
        '- 下面只给一条晨报条目，请只输出一个 JSON 对象，不要输出数组、Markdown 或解释。\n'
        '- `summary_main_existing_untrusted`、`why_it_matters_existing_untrusted` 只能作参考；如果它们和 title/body_text 冲突，必须以 title/body_text/url 为准重新写。\n'
        '- 不要因为原摘要已经是中文就沿用它；必须重新核对标题和正文后再成稿。\n'
        '- `display_summary` 不得复述标题，不得写成推荐理由，不得只写风险提醒或“需要关注”。\n'
        '- `display_points` 可以为空数组；没有干净、具体、中文的新信息时宁可不写要点，禁止塞入 Hacker News points/author、网页导航、财经行情、基金榜单或站点页脚。\n'
        '- 严禁跨条目串事实：ODoH/anonymous DNS relay 不能写成 AT&T Room 641A/Mark Klein/EFF；Claude for Small Business 不能混入与小企业产品无关的历史监听内容。\n'
        '- 安全公告必须写具体漏洞类型和直接后果；不要统一套用“权限绕过、敏感信息暴露或配置保护不足”。\n'
        '- 如果材料不足，也要基于标题、来源和可用正文写出具体主体、动作、对象、影响；不要使用空泛模板句。\n\n'
        '## 输入条目 JSON\n\n'
        f'{json.dumps(packet, ensure_ascii=False, indent=2)}\n'
    )


def _run_llm(prompt: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            [
                'openclaw', 'infer', 'model', 'run',
                '--json',
                '--model', LLM_MODEL,
                '--prompt', prompt,
            ],
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DisplayRewriteError('failed to run display rewrite model: openclaw command not found on PATH') from exc
    except Exception as exc:
        raise DisplayRewriteError(f'failed to run display rewrite model: {exc}') from exc

    if result.returncode != 0:
        stderr = _trim(result.stderr or '', 800)
        raise DisplayRewriteError(f'display rewrite model failed: {stderr}')
    payload_text = (result.stdout or '').strip()
    if not payload_text:
        raise DisplayRewriteError('display rewrite model returned empty output')
    try:
        payload = json.loads(payload_text)
    except Exception:
        return _parse_json_object(payload_text)
    text = _extract_text_from_infer_payload(payload)
    if text:
        return _parse_json_object(text)
    if isinstance(payload, dict):
        return payload
    raise DisplayRewriteError('display rewrite model returned unsupported payload')


def _normalize_llm_result(data: Dict[str, Any], item: Dict[str, Any], index: int) -> Dict[str, Any]:
    title = _clean_text(str(data.get('display_title') or data.get('title') or ''))
    summary = _clean_text(str(data.get('display_summary') or data.get('summary_main') or data.get('summary') or ''))
    points_raw = data.get('display_points') or data.get('key_points') or []
    if not isinstance(points_raw, list):
        points_raw = []
    points = [_clean_text(str(point)) for point in points_raw if _clean_text(str(point))]
    points = [point for point in points if point != summary][:3]
    drop = bool(data.get('drop_recommended'))
    drop_reason = _clean_text(str(data.get('drop_reason') or ''))

    problems = _validate_rewrite(title, summary, points, item, index, drop=drop, drop_reason=drop_reason)
    if problems:
        raise DisplayRewriteError(f'item #{index} display rewrite invalid: ' + '; '.join(problems))
    return {
        'display_title': title,
        'display_summary': summary,
        'display_points': points,
        'drop_recommended': drop,
        'drop_reason': drop_reason,
    }


def _validate_rewrite(
    title: str,
    summary: str,
    points: List[str],
    item: Dict[str, Any],
    index: int,
    *,
    drop: bool,
    drop_reason: str,
) -> List[str]:
    problems: List[str] = []
    source_type = str(item.get('source_type') or '')
    if drop:
        problems.append(f'drop_recommended is not allowed in formal Top10 output: {drop_reason or "no reason"}')
    if not _looks_chinese(title, min_chars=3):
        problems.append('display_title is not localized enough')
    if not _looks_chinese(summary, min_chars=28):
        problems.append('display_summary is too short or not Chinese enough')
    if len(summary) < 45:
        problems.append('display_summary is too thin')
    if _too_much_english(summary):
        problems.append('display_summary contains too much English')
    if _is_noise(summary) or _is_noise(title):
        problems.append('display output contains page noise')
    if _is_generic(summary) or _is_plain_generic(summary):
        problems.append('display_summary is generic filler')
    if _contains_known_cross_item_contamination(item, f'{title} {summary}'):
        problems.append('display_summary contains cross-item contamination')
    if _same_after_cleanup(title, summary):
        problems.append('display_summary just repeats title')
    mismatch = _topic_mismatch(item, title, summary)
    if mismatch:
        problems.append(mismatch)
    if source_type == 'github_advisory' and len(summary) < 80:
        problems.append('security advisory summary must explain affected object, risk, and action')
    if len(points) > 3:
        problems.append('too many display_points')
    for point in points:
        if _is_noise(point) or _too_much_english(point):
            problems.append('display_points contain noise or too much English')
            break
        if _is_generic(point) or _is_plain_generic(point) or _contains_known_cross_item_contamination(item, point):
            problems.append('display_points contain generic or mismatched copy')
            break
    return problems


def _quality_problems(items: List[Dict[str, Any]]) -> List[str]:
    problems: List[str] = []
    if len(items) != 10:
        problems.append(f'item_count={len(items)} expected=10')
    for idx, item in enumerate(items, 1):
        title = str(item.get('title_zh') or item.get('card_title') or '').strip()
        summary = str(item.get('summary_main') or item.get('card_summary') or '').strip()
        source_type = str(item.get('source_type') or '')
        row_problems = _validate_rewrite(title, summary, [str(x) for x in item.get('key_points') or []], item, idx, drop=False, drop_reason='')
        if row_problems:
            problems.append(f'#{idx} {title or item.get("title", "")}: {"; ".join(row_problems)}')
        if source_type == 'hackernews_top' and title.startswith('社区热议：') and len(summary) < 70:
            problems.append(f'#{idx} {title}: HN summary is too thin for final copy')
    return problems


def _build_final_payload(generated_at: Any, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'generated_at': generated_at,
        'headline': '今日 AI 早报',
        'lead': ' | '.join([str(item.get('summary_main') or '').strip() for item in items[:3] if str(item.get('summary_main') or '').strip()]),
        'count': len(items),
        'source_count': len(items),
        'items_used': [str(item.get('item_id') or '') for item in items],
        'generation_mode': 'display_rewrite_llm',
        'model': LLM_MODEL,
        'items': items,
    }


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise DisplayRewriteError(f'missing required input: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise DisplayRewriteError(f'failed to read JSON input {path}: {exc}') from exc
    if not isinstance(payload, dict):
        raise DisplayRewriteError(f'JSON input root must be an object: {path}')
    return payload


def _parse_json_object(text: str) -> Dict[str, Any]:
    raw = (text or '').strip()
    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        raise DisplayRewriteError('model output did not contain a JSON object')
    try:
        data = json.loads(match.group(0))
    except Exception as exc:
        raise DisplayRewriteError(f'failed to parse model JSON: {exc}') from exc
    if not isinstance(data, dict):
        raise DisplayRewriteError('model JSON root must be an object')
    return data


def _extract_text_from_infer_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ['output_text', 'text', 'content', 'result', 'message']:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data = payload.get('data')
        if isinstance(data, str) and data.strip():
            return data.strip()
    return ''


def _clean_for_prompt(text: str) -> str:
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    banned = [
        'GitHub Reviewed', 'Published May', 'Dependabot alerts', 'Hacker News item score=',
        'points by', 'author=', 'Show All Models', 'Skip to content', 'Navigation Menu',
        'Sign in', 'Sign up', 'We read every piece of feedback', 'Submit feedback',
        'Benchmarks Nifty', 'Motilal Oswal', 'Rate Story', 'English Edition', "Today's ePaper",
    ]
    for marker in banned:
        text = text.replace(marker, ' ')
    return re.sub(r'\s+', ' ', text).strip()


def _drop_untrusted_copy_if_dirty(item: Dict[str, Any], text: str) -> str:
    value = _clean_text(text)
    if not value:
        return ''
    if _is_noise(value) or _is_generic(value) or _is_plain_generic(value) or _too_much_english(value):
        return ''
    if _contains_known_cross_item_contamination(item, value):
        return ''
    return value


def _clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    return text.strip(' ，。;；')


def _looks_chinese(text: str, *, min_chars: int) -> bool:
    return len(re.findall(r'[\u4e00-\u9fff]', str(text or ''))) >= min_chars


def _too_much_english(text: str) -> bool:
    words = re.findall(r'[A-Za-z]{4,}', str(text or ''))
    zh = len(re.findall(r'[\u4e00-\u9fff]', str(text or '')))
    return len(words) >= 10 and zh < 55


def _is_noise(text: str) -> bool:
    markers = [
        'GitHub Reviewed', 'Published May', 'Updated May', 'Dependabot alerts',
        'Navigation Menu', 'Sign In Subscribe', 'Posts RSS', 'RSS Contact',
        'Hacker News item score=', 'points by', 'author=', 'Show All Models',
        'Skip to content', 'We read every piece of feedback', 'Submit feedback',
        'Benchmarks Nifty', 'Motilal Oswal', 'Rate Story', 'English Edition', "Today's ePaper",
        'OpenCode – Open source AI coding agent | Hacker News',
        'GitHub Copilot Coding Agent | Hacker News',
    ]
    return any(marker in str(text or '') for marker in markers)


def _is_generic(text: str) -> bool:
    markers = [
        '这条内容值得关注', '值得关注', '继续观察', '更适合作为背景信号',
        '围绕一个正在被开发者集中讨论的技术主题展开', '这是一个近期升温的开源项目',
        '这是一则安全公告', '重点在于说明受影响组件', '对应的是一个更具体的工程、产品或行业变化',
        '更像一个社区讨论入口', '适合作为补充阅读而不是主线内容',
    ]
    return any(marker in str(text or '') for marker in markers)


def _is_plain_generic(text: str) -> bool:
    value = str(text or '')
    markers = [
        '这条内容值得关注', '值得关注', '继续观察', '更适合作为背景信号',
        '这条 Hacker News 热门内容围绕一个技术主题展开', '这条安全公告重点在于说明受影响组件',
        '这是一个近期升温的开源项目', '更像一个社区讨论入口', '为什么会被开发者集中讨论',
        '适合作为补充阅读而不是主线内容', '帮助团队快速形成核查动作',
    ]
    return any(marker in value for marker in markers)


def _contains_known_cross_item_contamination(item: Dict[str, Any], text: str) -> bool:
    source = ' '.join([
        str(item.get('title') or ''),
        str(item.get('title_zh') or ''),
        str(item.get('url') or ''),
        str(item.get('body_text') or '')[:1400],
    ]).lower()
    output = str(text or '').lower()
    clusters = [
        (['odoh', 'oblivious dns', 'anonymous dns', 'dns relay', 'numa'], ['at&t', 'room 641a', 'mark klein', 'eff']),
        (['claude for small business', 'anthropic.com/news/claude-for-small-business'], ['at&t', 'room 641a', 'mark klein', 'eff']),
        (['strapi', 'cve-2026-22599', 'content type builder'], ['mistune', 'sharpcompress', 'ultrajson', 'lemmy']),
        (['opencode'], ['copilot coding agent', 'claude for small business', 'aws revenue']),
        (['copilot'], ['opencode', 'claude for small business']),
    ]
    if any(any(marker in source for marker in source_markers) and any(marker in output for marker in wrong_markers) for source_markers, wrong_markers in clusters):
        return True
    unrelated_fragments = ['benchmarks nifty', 'motilal oswal', 'rate story']
    return any(marker in output for marker in unrelated_fragments) and not any(marker in source for marker in unrelated_fragments)


def _same_after_cleanup(left: str, right: str) -> bool:
    def norm(value: str) -> str:
        return re.sub(r'[^0-9A-Za-z\u4e00-\u9fff]+', '', value or '').lower()

    lval = norm(left)
    rval = norm(right)
    return bool(lval and rval and (lval == rval or rval.startswith(lval)))


def _topic_mismatch(item: Dict[str, Any], title: str, summary: str) -> str:
    source = ' '.join([
        str(item.get('title') or ''),
        str(item.get('title_zh') or ''),
        str(item.get('url') or ''),
        str(item.get('body_text') or '')[:1400],
    ]).lower()
    output = f'{title} {summary}'.lower()
    marker_groups = [
        ('odoh relay', ['odoh', 'oblivious dns', 'anonymous dns', 'dns relay', 'numa'], ['at&t', 'room 641a', 'mark klein', 'eff']),
        ('strapi advisory', ['strapi', 'cve-2026-22599', 'content type builder'], ['mistune', 'sharpcompress', 'ultrajson', 'lemmy']),
        ('opencode', ['opencode'], ['copilot', 'claude for small business', 'aws revenue']),
        ('copilot', ['copilot'], ['opencode', 'claude for small business']),
    ]
    for label, source_markers, wrong_markers in marker_groups:
        if any(marker in source for marker in source_markers) and any(marker in output for marker in wrong_markers):
            return f'topic mismatch detected for {label}'
    return ''


def _trim(text: str, limit: int) -> str:
    value = str(text or '').strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)].rstrip() + '...'
