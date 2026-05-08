from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


MAX_CANDIDATES = 15
MAX_SELECTED = 10
BODY_PREVIEW_LIMIT = 4000
LLM_MODEL = 'hotai/gpt-5.4'
LLM_TIMEOUT_SECONDS = 45


def run_ai_triage(root: Path) -> Path:
    runtime = root / 'runtime'
    candidates = _read_items(runtime / 'top10_enriched_items.json') or _read_items(runtime / 'triage_candidates_enriched.json') or _read_items(runtime / 'triage_candidates.json')
    prepared = _prepare_candidates(candidates[:MAX_CANDIDATES])
    summarized = [_summarize_candidate(item) for item in prepared]
    selected = _select_top10(summarized)

    summarized_payload = {
        'generated_at': _now_iso(),
        'count': len(summarized),
        'items': summarized,
    }
    (runtime / 'triage_candidates_summarized.json').write_text(
        json.dumps(summarized_payload, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    payload = {
        'generated_at': _now_iso(),
        'selection_method': 'openclaw_ai_summary_rank_v1',
        'candidate_count': len(summarized),
        'count': len(selected),
        'items': selected,
    }
    out = runtime / 'ai_selected_top10.json'
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return out


def _read_items(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, dict):
        return []
    items = payload.get('items', [])
    return [item for item in items if isinstance(item, dict)]


def _prepare_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for item in items:
        row = dict(item)
        body_text = str(row.get('body_text_clean') or row.get('body_text') or '')
        row['ai_triage_input'] = {
            'item_id': row.get('item_id', ''),
            'title': row.get('title', ''),
            'source_name': row.get('source_name', ''),
            'source_type': row.get('source_type', ''),
            'url': row.get('url', ''),
            'priority': row.get('priority', ''),
            'impact_score': row.get('impact_score', 0),
            'confidence': row.get('confidence', 0),
            'reasons': row.get('reasons', []),
            'summary': row.get('summary', ''),
            'body_fetch_status': row.get('body_fetch_status', ''),
            'summary_basis': row.get('summary_basis', ''),
            'body_preview': body_text[:BODY_PREVIEW_LIMIT],
        }
        prepared.append(row)
    return prepared


def _summarize_candidate(item: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(item)
    title = str(row.get('title') or '').strip()
    source_name = str(row.get('source_name') or '').strip()
    source_type = str(row.get('source_type') or '').strip()
    body = str(row.get('body_text_clean') or row.get('body_text') or row.get('summary') or '').strip()
    summary_basis = str(row.get('summary_basis') or 'metadata_only').strip()
    body_length = int(row.get('body_length') or len(body))

    llm_summary = _maybe_llm_newspaper_summary(row)
    if llm_summary:
        summary_main = str(llm_summary.get('summary_main') or '').strip() or _build_summary_main(title, body, summary_basis)
        key_points = [str(x).strip() for x in llm_summary.get('key_points', []) if str(x).strip()][:3] or _build_key_points(title, body, source_type, source_name)
        why_it_matters = str(llm_summary.get('why_it_matters') or '').strip() or str(row.get('why_it_matters') or _build_why_it_matters(title, body, source_type, source_name)).strip()
        row['summary_generation_method'] = 'llm'
    else:
        summary_main = _build_summary_main(title, body, summary_basis)
        key_points = _build_key_points(title, body, source_type, source_name)
        why_it_matters = str(row.get('why_it_matters') or _build_why_it_matters(title, body, source_type, source_name)).strip()
        row['summary_generation_method'] = 'rule'
    warnings = _build_summary_warnings(title, summary_main, summary_basis, body_length)
    summary_confidence = _summary_confidence(summary_basis, body_length, warnings)

    topic_relevance_score = _topic_relevance_score(title, body, source_type, source_name)
    content_value_score = _content_value_score(body, source_type, source_name)
    summary_quality_score = _summary_quality_score(summary_main, key_points, warnings)
    confidence_score = _confidence_score(summary_confidence)
    final_ai_score = round(
        0.35 * topic_relevance_score +
        0.30 * content_value_score +
        0.20 * summary_quality_score +
        0.15 * confidence_score,
        4,
    )

    row.update({
        'summary_main': summary_main,
        'summary_zh': summary_main,
        'key_points': key_points,
        'why_it_matters': why_it_matters,
        'summary_confidence': summary_confidence,
        'summary_warnings': warnings,
        'topic_relevance_score': topic_relevance_score,
        'content_value_score': content_value_score,
        'summary_quality_score': summary_quality_score,
        'confidence_score': confidence_score,
        'final_ai_score': final_ai_score,
    })
    return row


def _maybe_llm_newspaper_summary(item: Dict[str, Any]) -> Dict[str, Any] | None:
    basis = str(item.get('summary_basis') or '')
    body_length = int(item.get('body_length') or 0)
    source_type = str(item.get('source_type') or '')
    if basis != 'full_text' or body_length < 1200:
        return None
    if source_type == 'github_high_stars':
        return None
    prompt = _build_llm_prompt(item)
    if not prompt:
        return None
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
    except Exception:
        return None

    if result.returncode != 0:
        return None
    payload_text = (result.stdout or '').strip()
    if not payload_text:
        return None
    try:
        payload = json.loads(payload_text)
    except Exception:
        return _parse_llm_summary_text(payload_text)

    text = _extract_text_from_infer_payload(payload)
    if not text:
        return None
    parsed = _parse_llm_summary_text(text)
    return parsed


def _build_llm_prompt(item: Dict[str, Any]) -> str:
    title = _trim(str(item.get('title') or '').strip(), 200)
    source_name = _trim(str(item.get('source_name') or '').strip(), 80)
    source_type = _trim(str(item.get('source_type') or '').strip(), 80)
    url = _trim(str(item.get('url') or '').strip(), 200)
    summary_basis = _trim(str(item.get('summary_basis') or '').strip(), 40)
    fallback_summary = _trim(str(item.get('summary') or '').strip(), 500)
    body = _trim(_clean_for_llm(str(item.get('body_text_clean') or item.get('body_text') or '')), BODY_PREVIEW_LIMIT)
    if not body and not fallback_summary:
        return ''
    return (
        '你是中文科技晨报编辑。请基于下面提供的材料，写成适合网页晨报展示的中文内容总结。\n\n'
        '核心目标：summary_main 必须像真正晨报编辑写的“主要内容”，先讲这条到底讲了什么，再讲影响；要自然、具体、有信息量，不要像系统说明、项目资料卡或网页残片。summary_main 默认写成 2~3 句，不要只给一句过薄的短概括。\n\n'
        '要求：\n'
        '1. 不要复述标题，不要照抄原文，不要输出网页导航、登录提示、评论区噪音。\n'
        '2. summary_main 必须先回答“这条到底讲了什么”，写成像晨报正文的人话摘要；先讲事件/产品/漏洞/观点本身，再讲影响。尽量覆盖主线、事实承接、变化落点这 2~3 层信息，而不是只给一句很薄的标签式概括。\n'
        '3. why_it_matters 只能补充“为什么值得看”，不能重复 summary_main，也不能写成空泛套话。\n'
        '4. 禁止输出这类空话或编辑腔：如“值得关注”“引发持续讨论”“围绕某个技术主题展开”“重点在于说明”“对应某种行业变化”“这是一条安全公告”“这是一个近期在 GitHub 上升温的开源项目”。\n'
        '5. 禁止输出这类脏内容：网页导航、登录提示、反爬页提示、README 目录串、评论数、点赞数、作者名、GitHub Advisory Database 页面 chrome、邮件列表页头。\n'
        '6. summary_main 和 why_it_matters 必须用自然中文完整改写，不能直接复制英文句子；允许保留产品名、公司名、漏洞编号等专有名词。\n'
        '7. key_points 也必须写成中文要点，禁止直接粘贴英文原句。\n'
        '8. 如果正文不足或可信度有限，要保守表述，但仍要尽量说清楚“已知主线是什么”；不要用空泛模板句顶上。即使信息有限，也优先补足主体、动作、对象、结果中的至少两项。\n'
        '9. 按来源类型把握口径：\n'
        '   - Hacker News/讨论帖：先写讨论对象、事件或核心观点本身，禁止写“引发持续讨论”当主摘要。\n'
        '   - 安全公告：先写受影响对象、利用方式/触发条件、风险结果，禁止写“重点在于说明受影响组件”。\n'
        '   - GitHub 项目：先写项目做什么、解决什么问题、为什么被关注，禁止写 stars/forks/语言资料卡。\n'
        '10. 仅输出 JSON，不要输出解释、代码块或额外文字。\n\n'
        '正面案例（合格风格）：\n'
        '{"summary_main":"这条内容讲的是 Instructure 旗下教学平台 Canvas 在疑似勒索软件事件后发生服务中断，攻击者还威胁泄露学校数据。报道把焦点放在服务可用性与数据泄露风险同时抬升这件事上，因为学校对关键 SaaS 的依赖一旦出问题，影响往往会从课堂运行迅速扩散到敏感数据保护。","why_it_matters":"它提醒学校和企业，关键 SaaS 一旦出问题，影响往往不只停留在服务可用性，还会迅速扩大到数据安全和业务连续性。","key_points":["Canvas 发生服务中断。","攻击者威胁泄露学校数据。","风险同时涉及可用性和敏感数据。"]}\n'
        '{"summary_main":"这条公告讲的是 utcp-http 在复用 OpenAPI 里声明的 servers[0].url 时没有重新做边界校验，攻击者可以借此把工具调用引向内部地址，进一步把 agent 变成盲 SSRF 跳板。问题的关键不只是一次错误请求，而是工具调用链把原本应该被拦住的内部地址重新暴露给了外部输入。","why_it_matters":"它暴露出 agent 工具调用链里的信任边界问题，影响不只是一条 HTTP 请求，而是整个工具执行面。","key_points":["OpenAPI 声明地址被直接复用。","攻击者可诱导工具请求内部地址。","风险可扩展到内网探测和云元数据访问。"]}\n'
        '{"summary_main":"马斯克正推动 X 继续向支付和金融服务延伸，其中一项银行或支付工具已接近推出。彭博的报道说明，X 的目标已经不只是维持社交平台形态，而是继续往交易、支付和更完整的“超级应用”能力靠拢。","why_it_matters":"如果工具真正上线，X 的平台边界会进一步从内容分发走向金融服务。","key_points":["X 正推动支付/银行工具落地。","平台定位向超级应用延伸。","重点不再只是社交分发。"]}\n\n'
        '反面案例（不合格，禁止模仿）：\n'
        '{"summary_main":"这条 Hacker News 热门内容围绕一个正在被开发者集中讨论的技术主题展开。"}\n'
        '{"summary_main":"这条安全公告重点在于说明受影响组件、触发条件、可能结果以及短期修复或缓解方向。"}\n'
        '{"summary_main":"这是一个近期在 GitHub 上升温的开源项目，目前约 1200 星、190 forks，主要语言是 Python。"}\n'
        '{"summary_main":"GitHub Advisory Database GitHub Reviewed ..."}\n\n'
        '输出 JSON 格式：\n'
        '{"summary_main":"...","why_it_matters":"...","key_points":["...","...","..."]}\n\n'
        f'标题: {title}\n'
        f'来源名称: {source_name}\n'
        f'来源类型: {source_type}\n'
        f'链接: {url}\n'
        f'正文依据: {summary_basis}\n'
        f'备用摘要: {fallback_summary}\n'
        f'正文内容:\n{body}\n'
    )


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


def _parse_llm_summary_text(text: str) -> Dict[str, Any] | None:
    raw = (text or '').strip()
    if not raw:
        return None
    m = re.search(r'\{[\s\S]*\}', raw)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    summary_main = str(data.get('summary_main') or '').strip()
    why_it_matters = str(data.get('why_it_matters') or '').strip()
    key_points = data.get('key_points') or []
    if not isinstance(key_points, list):
        key_points = []
    key_points = [_trim(str(x).strip(), 120) for x in key_points if str(x).strip()][:3]
    if not summary_main:
        return None
    if _looks_mostly_english(summary_main):
        return None
    if why_it_matters and _looks_mostly_english(why_it_matters):
        why_it_matters = ''
    blocked_summary_markers = [
        '围绕一个正在被开发者集中讨论的技术主题展开',
        '重点在于说明受影响组件',
        '这是一个近期在 GitHub 上升温的开源项目',
        'GitHub Advisory Database',
        'You are seeing this because',
        'Anubis',
        'English README',
        '完整目录',
    ]
    if any(marker in summary_main for marker in blocked_summary_markers):
        return None
    key_points = [p for p in key_points if not _looks_mostly_english(p)]
    return {
        'summary_main': _trim(summary_main, 180),
        'why_it_matters': _trim(why_it_matters, 120),
        'key_points': key_points,
    }


def _clean_for_llm(text: str) -> str:
    clean = _normalize_body_text(text)
    lines = re.split(r'(?<=[。！？.!?])\s+|\n+', clean)
    kept = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        lower = s.lower()
        if any(bad in lower for bad in [
            'you signed in', 'you signed out', 'navigation menu', 'skip to content', 'cookie policy',
            'privacy policy', 'terms', 'marketplace', 'github copilot', 'search code, repositories',
            'use saved searches', 'include my email address', 'sign in to github', 'reload to refresh your session',
            'all available qualifiers', 'we read every piece of feedback', 'share this article', 'advertisement',
            'github advisory database', 'hacker news item score=', 'author=priorityleft', 'anubis to protect the server',
            'linux kernel runtime guard free & open source for any platform', 'free & open source for unix'
        ]):
            continue
        if _looks_noisy(s):
            continue
        kept.append(s)
    return ' '.join(kept)


def _looks_mostly_english(text: str) -> bool:
    s = (text or '').strip()
    if not s:
        return False
    zh = len(re.findall(r'[\u4e00-\u9fff]', s))
    latin = len(re.findall(r'[A-Za-z]', s))
    return zh < 8 and latin > 30


def _build_summary_main(title: str, body: str, basis: str) -> str:
    text = _normalize_body_text(body)
    if not text:
        return _trim(title, 120)

    repo_summary = _github_snapshot_summary(text)
    if repo_summary:
        return repo_summary

    security_summary = _security_summary(text, title)
    if security_summary:
        return security_summary

    official_summary = _official_summary(title, text)
    if official_summary:
        return official_summary

    article_summary = _article_summary(title, text, basis)
    return article_summary or _trim(title, 120)


def _build_key_points(title: str, body: str, source_type: str, source_name: str) -> List[str]:
    text = _normalize_body_text(body)
    repo_points = _github_snapshot_points(text)
    if repo_points:
        return repo_points[:3]

    security_points = _security_points(text)
    if security_points:
        return security_points[:3]

    candidates = _split_points(text)
    points: List[str] = []
    for point in candidates:
        point = point.strip(' -•')
        if len(point) < 24:
            continue
        if _looks_noisy(point):
            continue
        if point not in points:
            points.append(_trim(point, 140))
        if len(points) >= 3:
            break
    if not points:
        points = [_trim(title, 100)]
    if source_type == 'github_advisory':
        points.insert(0, '这是一条安全相关信息，需要确认是否影响现有依赖或部署环境。')
    elif source_name.startswith('SEC') or '美联储' in source_name:
        points.insert(0, '这是一条官方或监管动态，重点在于政策、市场或制度层面的变化。')
    return points[:3]


def _build_why_it_matters(title: str, body: str, source_type: str, source_name: str) -> str:
    text = f"{title} {body}".lower()
    if source_type == 'github_advisory':
        return '这类漏洞信息会直接影响依赖安全、权限控制或数据暴露风险，适合作为晨报中的风险信号。'
    if source_type == 'github_high_stars':
        return '它反映了开源社区最近在关注什么工具和工作流，有助于判断 AI 开发栈的热点变化。'
    if source_type == 'hackernews_top':
        return '它是社区正在集中讨论的话题，通常能较早反映开发者和从业者的关注点变化。'
    if source_name.startswith('SEC') or '美联储' in source_name:
        return '它属于官方或监管层面的变化，虽然不一定是技术主线，但可能影响行业环境和资本市场预期。'
    if any(k in text for k in ['agent', 'llm', 'model', 'inference', 'benchmark', 'multimodal']):
        return '它和 AI 模型、Agent 工具链或推理能力直接相关，值得进入晨报主榜。'
    if any(k in text for k in ['release', 'launch', 'customer', 'enterprise', 'funding', 'acquisition']):
        return '它释放了产品发布、企业采用或商业化推进信号，适合保留在今日重点中。'
    return '它具备一定信息密度，可以作为今日晨报中的补充观察。'


def _build_summary_warnings(title: str, summary_main: str, basis: str, body_length: int) -> List[str]:
    warnings: List[str] = []
    if basis != 'full_text':
        warnings.append('未获取完整正文')
    if body_length < 300:
        warnings.append('正文长度较短')
    if _similarity_title_summary(title, summary_main):
        warnings.append('摘要疑似接近标题复述')
    if _is_generic_summary(summary_main):
        warnings.append('摘要信息密度偏低')
    return warnings


def _summary_confidence(basis: str, body_length: int, warnings: List[str]) -> str:
    if basis == 'full_text' and body_length >= 600 and len(warnings) <= 1:
        return 'high'
    if basis in {'full_text', 'partial_text'} and body_length >= 180:
        return 'medium'
    return 'low'


def _topic_relevance_score(title: str, body: str, source_type: str, source_name: str) -> float:
    text = f"{title} {body} {source_type} {source_name}".lower()
    score = 0.45
    keywords = ['ai', 'agent', 'llm', 'model', 'inference', 'prompt', 'mcp', 'open source', 'github', 'multimodal']
    score += min(0.4, sum(0.06 for kw in keywords if kw in text))
    if source_type == 'github_advisory':
        score += 0.08
    return min(1.0, round(score, 4))


def _content_value_score(body: str, source_type: str, source_name: str) -> float:
    length = len(body or '')
    score = 0.35
    if length >= 1200:
        score += 0.35
    elif length >= 600:
        score += 0.25
    elif length >= 250:
        score += 0.15
    if source_type == 'github_advisory':
        score += 0.15
    if source_name.startswith('SEC') or '美联储' in source_name:
        score += 0.05
    return min(1.0, round(score, 4))


def _summary_quality_score(summary_main: str, key_points: List[str], warnings: List[str]) -> float:
    score = 0.6
    if len(summary_main) >= 60:
        score += 0.12
    if len(key_points) >= 2:
        score += 0.12
    score -= 0.1 * len(warnings)
    return max(0.1, min(1.0, round(score, 4)))


def _confidence_score(level: str) -> float:
    return {'high': 0.95, 'medium': 0.7, 'low': 0.4}.get(level, 0.4)


def _select_top10(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = sorted(items, key=_rank_key, reverse=True)
    rows = []
    for idx, item in enumerate(ranked[:MAX_SELECTED], 1):
        rows.append({
            'rank': idx,
            'item_id': item.get('item_id', ''),
            'priority': item.get('priority', 'Important'),
            'title_zh': item.get('title_zh') or item.get('title') or '(untitled)',
            'title_en': item.get('title_en') or item.get('title') or '(untitled)',
            'summary_zh': item.get('summary_main') or item.get('summary_llm') or item.get('summary') or '',
            'summary_en': item.get('summary') or '',
            'key_points': item.get('key_points', []),
            'why_it_matters': item.get('why_it_matters', ''),
            'summary_basis': item.get('summary_basis', ''),
            'summary_confidence': item.get('summary_confidence', 'low'),
            'summary_warnings': item.get('summary_warnings', []),
            'source_name': item.get('source_name', ''),
            'source_type': item.get('source_type', ''),
            'published_at': item.get('published_at', ''),
            'url': item.get('url', ''),
            'final_ai_score': item.get('final_ai_score', 0),
        })
    return rows


def _rank_key(item: Dict[str, Any]) -> tuple:
    priority = str(item.get('priority', 'FYI'))
    priority_rank = {'Urgent': 3, 'Important': 2, 'FYI': 1}.get(priority, 0)
    return (
        priority_rank,
        float(item.get('final_ai_score', 0) or 0),
        float(item.get('impact_score', 0) or 0),
        float(item.get('confidence', 0) or 0),
    )


def _normalize_body_text(text: str) -> str:
    clean = (text or '').replace('&mdash;', '—').replace('&nbsp;', ' ').replace('&quot;', '"')
    clean = clean.replace('&amp;', '&').replace('&#x27;', "'")
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _github_snapshot_summary(text: str) -> str:
    if 'GitHub high-star repo snapshot.' not in text:
        return ''
    stars = _match_group(text, r'stars=(\d+)')
    forks = _match_group(text, r'forks=(\d+)')
    language = _match_group(text, r'language=([^|]+)')
    desc = _after_last_bar(text)
    parts = []
    if stars:
        parts.append(f'目前约 {stars} 星')
    if forks:
        parts.append(f'{forks} forks')
    if language:
        parts.append(f'主要语言是 {language.strip()}')
    metric = '，'.join(parts)
    if metric:
        metric = f'，{metric}'
    desc = _trim(desc, 120)
    if not desc:
        return ''
    if '提示词' in desc or 'prompt' in desc.lower():
        return f"这个项目围绕提示词组织与复用展开，核心是把分散的提示词整理成可直接使用的场景化目录。它当前体现的不是单一模型能力，而是提示词资产开始被当成可复用的工作流素材来管理。"
    if '推理' in desc or 'inference' in desc.lower() or 'latency' in desc.lower() or 'throughput' in desc.lower():
        return f"这个项目主要在做模型推理加速，重点放在延迟、吞吐或执行效率优化上。它反映的是推理基础设施竞争正在从单点模型效果，进一步走向更底层的系统效率。"
    return f"这个项目主要在做：{desc}。它反映的是相关能力正在从概念介绍走向更具体的产品化或工程化落地。"


def _github_snapshot_points(text: str) -> List[str]:
    if 'GitHub high-star repo snapshot.' not in text:
        return []
    stars = _match_group(text, r'stars=(\d+)')
    forks = _match_group(text, r'forks=(\d+)')
    language = _match_group(text, r'language=([^|]+)')
    desc = _after_last_bar(text)
    points = []
    if desc:
        points.append(_trim(desc, 120))
    if stars or forks:
        metrics = []
        if stars:
            metrics.append(f"约 {stars} 星")
        if forks:
            metrics.append(f"{forks} forks")
        points.append('社区热度：' + '，'.join(metrics))
    if language:
        points.append(f"主要技术栈：{language.strip()}")
    return points


def _security_summary(text: str, title: str) -> str:
    lowered = text.lower()
    if 'severity=' not in lowered and 'vulnerability' not in lowered and 'cve-' not in lowered and 'sql injection' not in lowered:
        return ''
    severity = _match_group(text, r'severity=([a-zA-Z]+)')
    impact = _section_after(text, '### Impact') or _section_after(text, '### Summary') or text
    sev_text = f"，严重程度为{_severity_zh(severity)}" if severity else ''
    return f"这是一条安全公告{sev_text}，核心问题是：{_trim(impact, 150)}"


def _security_points(text: str) -> List[str]:
    points = []
    impact = _section_after(text, '### Impact')
    patches = _section_after(text, '### Patches')
    workarounds = _section_after(text, '### Workarounds')
    summary = _section_after(text, '### Summary')
    for section in [summary, impact, patches, workarounds]:
        if section:
            points.append(_trim(section, 150))
        if len(points) >= 3:
            break
    return points


def _official_summary(title: str, text: str) -> str:
    lower = f"{title} {text}".lower()
    if 'securities and exchange commission' in lower or 'federal reserve' in lower or 'sec ' in lower:
        return f"这是一条官方发布，主要内容是：{_trim(text, 150)}"
    return ''


def _article_summary(title: str, text: str, basis: str) -> str:
    sentences = _split_points(text)
    useful = [s for s in sentences if len(s) >= 35 and not _looks_noisy(s)]
    if not useful:
        return _trim(text or title, 150)
    joined = ' '.join(useful[:2])
    if basis == 'partial_text':
        return f"根据已抓取到的正文，这条内容主要讲的是：{_trim(joined, 170)}"
    if basis == 'metadata_only':
        return f"从现有摘要信息看，这条内容主要讲的是：{_trim(joined, 170)}"
    return _trim(joined, 170)


def _looks_noisy(text: str) -> bool:
    lower = (text or '').lower()
    bad_markers = ['github high-star repo snapshot', 'hacker news item score', 'comments=', 'author=', 'we read every piece of feedback']
    return any(marker in lower for marker in bad_markers)


def _section_after(text: str, marker: str) -> str:
    if marker not in text:
        return ''
    tail = text.split(marker, 1)[1].strip(' |:-')
    parts = re.split(r'###\s+[A-Za-z]+', tail)
    return _trim(parts[0].strip(), 180) if parts else ''


def _after_last_bar(text: str) -> str:
    parts = [p.strip() for p in text.split('|') if p.strip()]
    return parts[-1] if parts else text


def _match_group(text: str, pattern: str) -> str:
    m = re.search(pattern, text or '', flags=re.IGNORECASE)
    return m.group(1).strip() if m else ''


def _severity_zh(value: str) -> str:
    return {'critical': '严重', 'high': '高危', 'medium': '中危', 'low': '低危'}.get((value or '').lower(), value)


def _sentences(text: str, limit: int = 3) -> str:
    clean = re.sub(r'\s+', ' ', text or '').strip()
    if not clean:
        return ''
    parts = re.split(r'(?<=[。！？.!?])\s+', clean)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return _trim(clean, 220)
    joined = ' '.join(parts[:limit])
    return _trim(joined, 260)


def _split_points(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r'(?<=[。！？.!?])\s+|\n+', text)
    return [re.sub(r'\s+', ' ', p).strip() for p in parts if p.strip()]


def _trim(text: str, max_chars: int) -> str:
    clean = re.sub(r'\s+', ' ', text or '').strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + '...'


def _similarity_title_summary(title: str, summary: str) -> bool:
    title_tokens = set(re.findall(r'[a-zA-Z0-9\u4e00-\u9fff]+', (title or '').lower()))
    summary_tokens = set(re.findall(r'[a-zA-Z0-9\u4e00-\u9fff]+', (summary or '').lower()))
    if not title_tokens or not summary_tokens:
        return False
    overlap = len(title_tokens & summary_tokens) / max(1, len(title_tokens))
    return overlap >= 0.8


def _is_generic_summary(summary: str) -> bool:
    generic_markers = ['值得关注', '引发讨论', '具备一定信息密度', '可作为今日候选', '主要围绕']
    return any(marker in (summary or '') for marker in generic_markers) and len(summary or '') < 90


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()