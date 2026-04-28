from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.models import CollectedItem, item_from_fields, utc_now_iso


def collect_openclaw_tavily(config: Dict[str, Any], *, root: Path, runtime_config: Dict[str, Any]) -> List[CollectedItem]:
    plan = build_tavily_search_plan(config)
    runtime_dir = root / str(runtime_config.get("output_dir", "runtime"))
    plan_path = runtime_dir / str(runtime_config.get("tavily_search_plan_file", "tavily_search_plan.json"))
    results_path = runtime_dir / str(runtime_config.get("tavily_search_results_file", "tavily_search_results.json"))
    write_tavily_search_plan(plan, plan_path)
    return read_tavily_search_results(results_path)


def build_tavily_topic_plan(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    section = config.get("openclaw_tavily_search", {})
    if not isinstance(section, dict) or not section.get("enabled", False):
        return []
    topics = section.get("topics", [])
    if not isinstance(topics, list):
        return []
    return [topic for topic in topics if isinstance(topic, dict)]


def build_tavily_search_plan(config: Dict[str, Any]) -> Dict[str, Any]:
    section = config.get("openclaw_tavily_search", {})
    if not isinstance(section, dict) or not section.get("enabled", False):
        return {"enabled": False, "items": []}

    max_items = int(section.get("max_items_per_topic", 5) or 5)
    recency_days = int(section.get("recency_days", 3) or 3)
    fallback_recency_days = int(section.get("fallback_recency_days", 7) or 7)
    skill_name = str(section.get("skill_name", "tavily-search")).strip() or "tavily-search"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    since = (now - timedelta(days=max(1, recency_days))).date().isoformat()
    fallback_since = (now - timedelta(days=max(recency_days, fallback_recency_days))).date().isoformat()
    topics = build_tavily_topic_plan(config)
    items = []
    for topic in topics:
        topic_id = str(topic.get("id", "")).strip()
        query = str(topic.get("query", "")).strip()
        if not topic_id or not query:
            continue
        domains = topic.get("domains", [])
        if not isinstance(domains, list):
            domains = []
        items.append(
            {
                "topic_id": topic_id,
                "topic_name": str(topic.get("name") or topic_id).strip(),
                "query": query,
                "domains": [str(domain).strip() for domain in domains if str(domain).strip()],
                "max_items": max_items,
                "recency_days": recency_days,
                "since_date": since,
                "fallback_recency_days": fallback_recency_days,
                "fallback_since_date": fallback_since,
            }
        )

    return {
        "enabled": True,
        "generated_at": utc_now_iso(),
        "skill_name": skill_name,
        "instructions": "请由 OpenClaw 调用 tavily-search skill 执行每日早报搜索。只收录近 3 天内信息；若某主题不足 max_items 条，宁可少于 max_items 条，也不要使用更旧内容。",
        "recency_policy": {
            "primary_days": recency_days,
            "fallback_days": fallback_recency_days,
            "primary_since_date": since,
            "fallback_since_date": fallback_since,
            "strict_max_days": 3,
            "avoid_repeating_previous_briefings": True,
        },
        "items": items,
    }


def write_tavily_search_plan(plan: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def read_tavily_search_results(path: Path) -> List[CollectedItem]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    raw_items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(raw_items, list):
        return []

    items: List[CollectedItem] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item = _item_from_tavily_result(raw)
        if item is not None:
            items.append(item)
    return items


def _item_from_tavily_result(raw: Dict[str, Any]) -> CollectedItem | None:
    title = _text(raw.get("title"))
    url = _text(raw.get("url"))
    if not title or not url:
        return None
    topic_id = _text(raw.get("topic_id"))
    source_name = _text(raw.get("source_name") or raw.get("source") or "OpenClaw Tavily")
    summary = _text(raw.get("summary") or raw.get("content") or raw.get("snippet"))
    published_at = _text(raw.get("published_at") or raw.get("published_date"))
    fetched_at = _text(raw.get("fetched_at")) or utc_now_iso()
    return item_from_fields(
        channel="openclaw_tavily",
        source_type="tavily_skill",
        source_id=f"openclaw_tavily:{topic_id or 'general'}",
        source_name=source_name,
        topic_id=topic_id,
        title=title,
        summary=summary,
        url=url,
        published_at=published_at,
        fetched_at=fetched_at,
    )


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()
