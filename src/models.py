from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict


@dataclass
class CollectedItem:
    item_id: str
    channel: str
    source_type: str
    source_id: str
    source_name: str
    topic_id: str
    title: str
    summary: str
    url: str
    published_at: str
    fetched_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TriageItem:
    item_id: str
    channel: str
    source_type: str
    source_id: str
    source_name: str
    topic_id: str
    title: str
    summary: str
    url: str
    published_at: str
    fetched_at: str
    priority: str
    impact_score: int
    confidence: float
    reasons: list[str]
    suggested_action: str
    short_summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_item_id(source_id: str, title: str, url: str) -> str:
    raw = f"{source_id}|{url}|{title}".encode("utf-8")
    return "sha1:" + hashlib.sha1(raw).hexdigest()


def item_from_fields(
    *,
    channel: str,
    source_type: str,
    source_id: str,
    source_name: str,
    topic_id: str = "",
    title: str,
    summary: str,
    url: str,
    published_at: str = "",
    fetched_at: str = "",
) -> CollectedItem:
    fetched = fetched_at or utc_now_iso()
    clean_title = " ".join((title or "").split()).strip() or "(untitled)"
    clean_url = (url or "").strip()
    return CollectedItem(
        item_id=make_item_id(source_id, clean_title, clean_url),
        channel=channel,
        source_type=source_type,
        source_id=source_id,
        source_name=source_name,
        topic_id=topic_id,
        title=clean_title,
        summary=" ".join((summary or "").split()).strip(),
        url=clean_url,
        published_at=published_at,
        fetched_at=fetched,
    )
