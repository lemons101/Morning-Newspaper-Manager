from __future__ import annotations

from typing import Iterable, List, Tuple

from src.models import CollectedItem, TriageItem


URGENT_KEYWORDS = [
    "critical vulnerability",
    "ransomware",
    "production down",
    "service outage",
    "legal notice",
    "urgent",
    "asap",
]

IMPORTANT_KEYWORDS = [
    "earnings",
    "acquisition",
    "funding",
    "ai",
    "agent",
    "deadline",
    "contract",
    "invoice",
    "action required",
]

AI_SIGNAL_KEYWORDS = [
    "ai",
    "agent",
    "mcp",
    "llm",
    "model",
    "openclaw",
    "openai",
    "anthropic",
    "deepmind",
    "huggingface",
    "inference",
    "multimodal",
    "coding agent",
    "enterprise ai",
]


def triage_items(items: Iterable[CollectedItem]) -> List[TriageItem]:
    triaged = [_triage_one(item) for item in items]
    return sorted(triaged, key=lambda item: (_priority_rank(item.priority), item.impact_score, item.confidence), reverse=True)


def _triage_one(item: CollectedItem) -> TriageItem:
    text = f"{item.title}\n{item.summary}\n{item.source_name}\n{item.source_type}".lower()
    score = 35
    reasons: List[str] = []

    urgent_hit = _first_hit(text, URGENT_KEYWORDS)
    important_hit = _first_hit(text, IMPORTANT_KEYWORDS)

    if item.channel == "mail_alert":
        score += 35
        reasons.append("mail alert channel")
        if item.title.lower().startswith("[urgent]"):
            score += 25
            reasons.append("mail classified as urgent")
        elif item.title.lower().startswith("[important]"):
            score += 15
            reasons.append("mail classified as important")

    if item.source_type == "github_advisory":
        ai_related = _has_ai_signal(text)
        score += 8
        reasons.append("GitHub security advisory")
        if ai_related:
            score += 10
            reasons.append("AI/tooling-related advisory")
        if "severity=critical" in text:
            score += 16 if ai_related else 8
            reasons.append("critical severity advisory")
        elif "severity=high" in text:
            score += 12 if ai_related else 5
            reasons.append("high severity advisory")
        elif "severity=medium" in text:
            score += 4 if ai_related else 0
            reasons.append("medium severity advisory")

    if item.source_id.startswith("sec_") or item.source_name.lower().startswith("sec "):
        score += 6
        reasons.append("official SEC source")

    if item.source_id.startswith("fed_") or "federal reserve" in item.source_name.lower():
        score += 4
        reasons.append("official Federal Reserve source")

    if item.source_type in {"github_high_stars", "hackernews_top"}:
        score += 18
        reasons.append("community trend signal")
        if _has_ai_signal(text):
            score += 18
            reasons.append("AI technical/community signal")

    if item.source_type == "tavily_skill":
        score += 22
        reasons.append("OpenClaw Tavily AI search signal")

    if urgent_hit:
        score += 30
        reasons.append(f"urgent keyword: {urgent_hit}")
    elif important_hit:
        score += 15
        reasons.append(f"important keyword: {important_hit}")

    score = max(0, min(100, score))
    priority = _priority_from_score(score)
    confidence = _confidence(priority, reasons)
    if not reasons:
        reasons.append("no strong business risk signal")

    return TriageItem(
        item_id=item.item_id,
        channel=item.channel,
        source_type=item.source_type,
        source_id=item.source_id,
        source_name=item.source_name,
        topic_id=item.topic_id,
        title=item.title,
        summary=item.summary,
        url=item.url,
        published_at=item.published_at,
        fetched_at=item.fetched_at,
        priority=priority,
        impact_score=score,
        confidence=confidence,
        reasons=reasons[:4],
        suggested_action=_suggested_action(priority, item.channel),
        short_summary=_short_summary(item.summary or item.title),
    )


def _priority_from_score(score: int) -> str:
    if score >= 80:
        return "Urgent"
    if score >= 50:
        return "Important"
    return "FYI"


def _priority_rank(priority: str) -> int:
    return {"Urgent": 3, "Important": 2, "FYI": 1}.get(priority, 0)


def _confidence(priority: str, reasons: List[str]) -> float:
    base = 0.55 + min(0.35, 0.08 * len(reasons))
    if priority == "Urgent":
        base += 0.05
    return round(min(0.97, base), 2)


def _suggested_action(priority: str, channel: str) -> str:
    if channel == "mail_alert" and priority == "Urgent":
        return "Review the email immediately and assign an owner."
    if priority == "Urgent":
        return "Review today, confirm business impact, and escalate if relevant."
    if priority == "Important":
        return "Include in today's briefing and decide whether follow-up is needed."
    return "Keep for awareness and archive after review."


def _short_summary(text: str, max_chars: int = 180) -> str:
    clean = " ".join((text or "").split()).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


def _first_hit(text: str, candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate and candidate in text:
            return candidate
    return ""


def _has_ai_signal(text: str) -> bool:
    return bool(_first_hit(text, AI_SIGNAL_KEYWORDS))
