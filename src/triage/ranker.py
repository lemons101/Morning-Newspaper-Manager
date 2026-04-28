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
    return _apply_top10_mix(ranked, limit=max(1, limit))


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


def _apply_top10_mix(items: List[TriageItem], *, limit: int) -> List[TriageItem]:
    selected: List[TriageItem] = []
    source_counts = {"github_advisory": 0, "rss_macro": 0}
    for item in items:
        if item.source_type == "github_advisory" and source_counts["github_advisory"] >= 2:
            continue
        if _is_macro_source(item) and source_counts["rss_macro"] >= 1:
            continue
        selected.append(item)
        if item.source_type == "github_advisory":
            source_counts["github_advisory"] += 1
        if _is_macro_source(item):
            source_counts["rss_macro"] += 1
        if len(selected) >= limit:
            return selected

    seen = {item.item_id for item in selected}
    for item in items:
        if item.item_id in seen:
            continue
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _is_macro_source(item: TriageItem) -> bool:
    source_id = item.source_id.lower()
    source_name = item.source_name.lower()
    return source_id.startswith(("sec_", "fed_")) or source_name.startswith("sec ") or "federal reserve" in source_name
