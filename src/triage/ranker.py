from __future__ import annotations

from typing import Iterable, List

from src.models import TriageItem


def select_triage_candidates(items: Iterable[TriageItem], *, limit: int = 25) -> List[TriageItem]:
    news_items = [item for item in items if item.channel != "mail_alert"]
    ranked = _rank_news_items(news_items)
    return ranked[: max(1, limit)]


def select_top_items(items: Iterable[TriageItem], *, limit: int = 10) -> List[TriageItem]:
    news_items = [item for item in items if item.channel != "mail_alert"]
    ranked = _rank_news_items(news_items)
    return _apply_editorial_mix(ranked, limit=max(1, limit))


def select_mail_alerts(items: Iterable[TriageItem]) -> List[TriageItem]:
    mail_items = [item for item in items if item.channel == "mail_alert"]
    return sorted(
        mail_items,
        key=lambda item: (_priority_rank(item.priority), item.impact_score, item.published_at),
        reverse=True,
    )


def _priority_rank(priority: str) -> int:
    return {"Urgent": 3, "Important": 2, "FYI": 1}.get(priority, 0)


def _rank_news_items(items: Iterable[TriageItem]) -> List[TriageItem]:
    return sorted(
        items,
        key=lambda item: (_priority_rank(item.priority), item.impact_score, item.confidence, item.published_at),
        reverse=True,
    )


def _apply_editorial_mix(items: List[TriageItem], *, limit: int) -> List[TriageItem]:
    selected: List[TriageItem] = []
    seen = set()

    buckets = [
        ("business_ai", 3),
        ("community_tools", 3),
        ("security", 1),
        ("macro", 1),
    ]

    for bucket_name, bucket_limit in buckets:
        bucket_items = [item for item in items if _bucket_for_item(item) == bucket_name and item.item_id not in seen]
        for item in bucket_items[:bucket_limit]:
            selected.append(item)
            seen.add(item.item_id)
            if len(selected) >= limit:
                return _rerank_selected(selected)

    for item in items:
        if item.item_id in seen:
            continue
        selected.append(item)
        seen.add(item.item_id)
        if len(selected) >= limit:
            break
    return _rerank_selected(selected)


def _is_macro_source(item: TriageItem) -> bool:
    source_id = item.source_id.lower()
    source_name = item.source_name.lower()
    return source_id.startswith(("sec_", "fed_")) or source_name.startswith("sec ") or "federal reserve" in source_name


def _bucket_for_item(item: TriageItem) -> str:
    if item.source_type == "github_advisory":
        return "security"
    if _is_macro_source(item):
        return "macro"
    if item.source_type in {"hackernews_top", "github_high_stars"}:
        return "community_tools"
    return "business_ai"


def _rerank_selected(items: List[TriageItem]) -> List[TriageItem]:
    return sorted(
        items,
        key=lambda item: (_priority_rank(item.priority), item.impact_score, item.confidence, item.published_at),
        reverse=True,
    )
