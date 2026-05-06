from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import html
import re


MAX_BODY_CHARS = 8000
MIN_FULLTEXT_CHARS = 600
MIN_PARTIAL_CHARS = 180


def enrich_candidates_with_content(items: List[Dict[str, Any]], *, root: Path, enabled: bool = True) -> List[Dict[str, Any]]:
    if not enabled:
        return [dict(item) for item in items]
    total = len(items)
    rows = [dict(item) for item in items]
    indexed_results: Dict[int, Dict[str, Any]] = {}
    max_workers = min(4, max(1, total))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for idx, row in enumerate(rows, 1):
            title = str(row.get("title", "")).strip()[:80]
            print(f"[正文富化开始] {idx}/{total} title={title}")
            future = executor.submit(_enrich_single_row, row)
            future_map[future] = idx
        for future in as_completed(future_map):
            idx = future_map[future]
            enriched_row = future.result()
            indexed_results[idx] = enriched_row
            print(
                f"[正文富化完成] {idx}/{total} status={enriched_row.get('body_fetch_status')} "
                f"basis={enriched_row.get('summary_basis')} len={enriched_row.get('body_length')}"
            )

    return [indexed_results[idx] for idx in range(1, total + 1)]


def _enrich_single_row(row: Dict[str, Any]) -> Dict[str, Any]:
    fetch = _fetch_body_for_item(row)
    body_clean = fetch["body_text_clean"]
    row.update(fetch)
    row["summary_llm"] = _build_summary_llm(row, body_clean)
    row["why_it_matters"] = _build_why_it_matters(row, body_clean)
    return row


def _fetch_body_for_item(item: Dict[str, Any]) -> Dict[str, Any]:
    source_type = str(item.get("source_type", ""))
    summary = str(item.get("summary", "") or "")
    url = str(item.get("url", "") or "").strip()
    fallback = _clean_text(summary)[:MAX_BODY_CHARS]

    if source_type == "github_advisory":
        return _build_fetch_result(
            raw_text=summary,
            clean_text=fallback,
            status="from_summary",
            basis="metadata_only",
            quality="partial",
            reason="github advisory 使用摘要字段作为正文来源",
        )
    if not url or url.startswith("mail:"):
        return _build_fetch_result(
            raw_text=summary,
            clean_text=fallback,
            status="no_url",
            basis="metadata_only",
            quality="unavailable",
            reason="无可抓取 URL，退化到摘要字段",
        )

    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 OpenClaw/1.0"})
        with urlopen(req, timeout=8) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read(200000)
        if "text/html" not in content_type and "text/plain" not in content_type:
            return _build_fetch_result(
                raw_text=summary,
                clean_text=fallback,
                status="unsupported_content_type",
                basis="metadata_only",
                quality="unavailable",
                reason=f"不支持的内容类型: {content_type}",
            )
        text = raw.decode("utf-8", errors="ignore")
        extracted = _extract_meaningful_text(text, url=url, source_type=source_type)
        clean = _clean_text(extracted)[:MAX_BODY_CHARS]
        if len(clean) >= MIN_FULLTEXT_CHARS:
            return _build_fetch_result(
                raw_text=text,
                clean_text=clean,
                status="fetched",
                basis="full_text",
                quality="good",
                reason="成功抓取并抽取到可用正文",
            )
        if len(clean) >= MIN_PARTIAL_CHARS:
            return _build_fetch_result(
                raw_text=text,
                clean_text=clean,
                status="partial",
                basis="partial_text",
                quality="partial",
                reason="抓取到部分正文，但长度有限",
            )
        if fallback:
            return _build_fetch_result(
                raw_text=summary,
                clean_text=fallback,
                status="too_short",
                basis="metadata_only",
                quality="poor",
                reason="正文抽取过短，退化到摘要字段",
            )
        return _build_fetch_result(
            raw_text=text,
            clean_text=clean,
            status="too_short",
            basis="partial_text",
            quality="poor",
            reason="正文抽取过短且缺少可用摘要",
        )
    except Exception as exc:
        return _build_fetch_result(
            raw_text=summary,
            clean_text=fallback,
            status="fetch_failed",
            basis="metadata_only",
            quality="unavailable",
            reason=f"抓取失败: {type(exc).__name__}",
        )


def _build_fetch_result(*, raw_text: str, clean_text: str, status: str, basis: str, quality: str, reason: str) -> Dict[str, Any]:
    return {
        "body_fetch_status": status,
        "body_text_raw": raw_text[:MAX_BODY_CHARS],
        "body_text_clean": clean_text[:MAX_BODY_CHARS],
        "body_text": clean_text[:MAX_BODY_CHARS],
        "body_length": len(clean_text[:MAX_BODY_CHARS]),
        "summary_basis": basis,
        "content_quality": quality,
        "extract_quality_reason": reason,
        "content_basis": basis,
    }


def _html_to_text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<noscript[\s\S]*?</noscript>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<svg[\s\S]*?</svg>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _extract_meaningful_text(html: str, *, url: str, source_type: str) -> str:
    host = urlparse(url).netloc.lower()

    if source_type == 'hackernews_top' and 'news.ycombinator.com' not in host:
        article = _extract_article_html(html)
        if article:
            html = article

    text = _html_to_text(html)

    if "github.com" in host and source_type == "github_high_stars":
        text = _extract_github_repo_text(text)
    elif "github.com" in host:
        text = _strip_github_noise(text)

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if len(line) >= 24]
    filtered = []
    for line in lines:
        lower = line.lower()
        if any(bad in lower for bad in [
            "skip to content", "sign in", "navigation menu", "all rights reserved", "cookie", "privacy policy",
            "github copilot", "marketplace", "documentation", "customer support", "search code, repositories",
            "home news sport business technology", "live weather newsletters", "javascript is disabled",
            "subscribe to our", "share this article", "advertisement", "use saved searches",
            "include my email address", "you signed in with another tab", "you signed out in another tab",
            "you switched accounts on another tab", "reload to refresh your session", "notifications", "fork",
            "star", "branches", "tags", "releases", "report repository", "saved searches", "table of contents",
            "back to top", "portfolio documentation"
        ]):
            continue
        if _looks_ui_noise(line):
            continue
        filtered.append(line)
    compact = "\n".join(filtered)
    compact = re.sub(r"\s+", " ", compact).strip()
    return compact


def _extract_github_repo_text(text: str) -> str:
    cleaned = _strip_github_noise(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    kept: List[str] = []
    readme_started = False
    for line in lines:
        lower = line.lower()
        if not readme_started and ('readme' in lower or 'description' in lower):
            readme_started = True
        if not readme_started:
            if any(k in lower for k in ['agent', 'llm', 'model', 'open-source', 'open source', 'framework', 'toolkit', 'sdk']):
                kept.append(line)
            continue
        if _looks_ui_noise(line):
            continue
        kept.append(line)
        if len(' '.join(kept)) >= 5000:
            break
    if kept:
        return '\n'.join(kept)
    return cleaned


def _strip_github_noise(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept = []
    for line in lines:
        lower = line.lower()
        if any(bad in lower for bad in [
            'github - ', 'github we read every piece of feedback', 'we read every piece of feedback',
            'include my email address', 'use saved searches', 'all available qualifiers', 'sign in to github',
            'you signed in with another tab', 'you signed out in another tab', 'you switched accounts on another tab',
            'reload to refresh your session', 'notifications', 'fork your own copy', 'report repository',
            'star notifications', 'saved searches', 'code issues pull requests actions projects wiki security insights'
        ]):
            continue
        kept.append(line)
    return '\n'.join(kept)


def _looks_ui_noise(text: str) -> bool:
    stripped = (text or '').strip()
    lower = stripped.lower()
    if len(stripped) < 8:
        return True
    if re.fullmatch(r'[\W\d_\-:/|]+', stripped):
        return True
    if sum(1 for ch in stripped if ch in ':/|>') >= 6:
        return True
    if lower.count('github') >= 2:
        return True
    return False


def _extract_article_html(raw_html: str) -> str:
    for pattern in [
        r'<article[^>]*>([\s\S]*?)</article>',
        r'<main[^>]*>([\s\S]*?)</main>',
        r'<div[^>]+class="[^"]*(post-content|entry-content|article-content|markdown-body|content)[^"]*"[^>]*>([\s\S]*?)</div>',
    ]:
        m = re.search(pattern, raw_html, flags=re.IGNORECASE)
        if not m:
            continue
        content = m.group(m.lastindex or 1)
        if content and len(content) > 400:
            return content
    return raw_html


def _clean_text(text: str) -> str:
    text = html.unescape(text or '')
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    deduped: List[str] = []
    seen = set()
    for line in lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    return "\n".join(deduped).strip()


def _build_summary_llm(item: Dict[str, Any], body: str) -> str:
    title = str(item.get("title", "")).strip()
    summary = str(item.get("summary", "")).strip()
    basis = str(item.get("summary_basis", "metadata_only"))
    body_excerpt = _first_meaningful_excerpt(body or summary or title, 320)
    if basis == "full_text":
        return body_excerpt
    if basis == "partial_text":
        return body_excerpt
    return body_excerpt


def _first_meaningful_excerpt(text: str, limit: int) -> str:
    clean = re.sub(r"\s+", " ", (text or "")).strip()
    return clean[:limit].rstrip() + ("..." if len(clean) > limit else "")


def _build_why_it_matters(item: Dict[str, Any], body: str) -> str:
    source_type = str(item.get("source_type", "")).strip()
    source_name = str(item.get("source_name", "")).strip()
    title = str(item.get("title", "")).strip().lower()
    text = f"{title} {(body or '')[:1200]}".lower()
    if source_type == "github_advisory":
        return "它可能影响现有依赖或基础设施安全，适合进入日报的风险信号位。"
    if any(k in text for k in ["funding", "acquisition", "enterprise", "customer", "launch", "release"]):
        return "它释放了商业化、产品发布或企业采用信号，适合进入晨报主榜。"
    if any(k in text for k in ["agent", "model", "llm", "multimodal", "benchmark", "inference"]):
        return "它和 AI 技术、Agent 工具链或模型进展直接相关，值得进入今日候选。"
    if source_name.startswith("SEC") or "美联储" in source_name:
        return "它属于官方/监管信号，可能影响资本市场或产业环境，但通常只适合少量保留。"
    return "它具备一定信息密度，适合作为今日候选进一步比较。"