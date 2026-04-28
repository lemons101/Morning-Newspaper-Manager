from __future__ import annotations

from typing import Any, Dict, List

from src.collectors.common import http_json, normalize_unix, positive_int
from src.models import CollectedItem, item_from_fields, utc_now_iso


def fetch_hackernews_top(source: Dict[str, Any], *, max_items: int) -> List[CollectedItem]:
    endpoint = str(source.get("endpoint", "https://hacker-news.firebaseio.com/v0")).rstrip("/")
    source_id = str(source.get("id", "hackernews_top")).strip()
    source_name = str(source.get("name", source_id)).strip()
    stories_type = str(source.get("stories_type", "topstories")).strip()
    if stories_type not in {"topstories", "newstories", "beststories"}:
        stories_type = "topstories"
    max_stories = positive_int(source.get("max_stories"), 20)
    timeout_seconds = positive_int(source.get("timeout_seconds"), 15)
    fetched_at = utc_now_iso()

    ids_payload = http_json(f"{endpoint}/{stories_type}.json", timeout_seconds=timeout_seconds)
    if not isinstance(ids_payload, list):
        return []

    items: List[CollectedItem] = []
    seen_urls = set()
    for raw_id in ids_payload[:max_stories]:
        if len(items) >= max_items:
            break
        try:
            story_id = int(raw_id)
        except (TypeError, ValueError):
            continue

        story = http_json(f"{endpoint}/item/{story_id}.json", timeout_seconds=timeout_seconds)
        if not isinstance(story, dict):
            continue
        if str(story.get("type", "")).strip() not in {"story", "job"}:
            continue

        url = str(story.get("url", "")).strip() or f"https://news.ycombinator.com/item?id={story_id}"
        if url in seen_urls:
            continue
        seen_urls.add(url)

        score = int(story.get("score", 0) or 0)
        comments = int(story.get("descendants", 0) or 0)
        author = str(story.get("by", "")).strip()
        text = str(story.get("text", "")).strip()
        summary_parts = [f"Hacker News item score={score}, comments={comments}"]
        if author:
            summary_parts.append(f"author={author}")
        if text:
            summary_parts.append(text)

        items.append(
            item_from_fields(
                channel="fixed_platform",
                source_type="hackernews_top",
                source_id=source_id,
                source_name=source_name,
                title=str(story.get("title", "")).strip() or f"HN story #{story_id}",
                summary=" | ".join(summary_parts),
                url=url,
                published_at=normalize_unix(story.get("time"), fetched_at),
                fetched_at=fetched_at,
            )
        )
    return items

