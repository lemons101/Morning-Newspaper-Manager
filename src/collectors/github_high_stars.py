from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any, Dict, Iterable, List
from urllib.parse import urlencode

from src.collectors.common import http_json, normalize_iso, positive_int
from src.models import CollectedItem, item_from_fields, utc_now_iso


def fetch_github_high_stars(source: Dict[str, Any], *, max_items: int) -> List[CollectedItem]:
    endpoint = str(source.get("endpoint", "https://api.github.com/search/repositories")).strip()
    source_id = str(source.get("id", "github_high_stars")).strip()
    source_name = str(source.get("name", source_id)).strip()
    auth_env = str(source.get("auth_env", "")).strip() or None
    per_query_limit = positive_int(source.get("per_query_limit"), 10)
    fetched_at = utc_now_iso()
    items: List[CollectedItem] = []
    seen_urls = set()

    for language, extra in _iter_query_specs(source):
        query = _build_query(source, language=language, extra=extra)
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": max(1, min(100, per_query_limit)),
        }
        payload = http_json(
            f"{endpoint}?{urlencode(params)}",
            headers=_github_headers(auth_env),
            timeout_seconds=20,
        )
        repos = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(repos, list):
            continue

        for repo in repos:
            if len(items) >= max_items:
                return items
            if not isinstance(repo, dict):
                continue
            url = str(repo.get("html_url", "")).strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            full_name = str(repo.get("full_name", "")).strip() or "(unknown repo)"
            stars = int(repo.get("stargazers_count", 0) or 0)
            forks = int(repo.get("forks_count", 0) or 0)
            language_value = str(repo.get("language", "")).strip()
            desc = str(repo.get("description") or "").strip()
            summary_parts = [f"GitHub high-star repo snapshot. stars={stars}, forks={forks}"]
            if language_value:
                summary_parts.append(f"language={language_value}")
            if desc:
                summary_parts.append(desc)

            items.append(
                item_from_fields(
                    channel="fixed_platform",
                    source_type="github_high_stars",
                    source_id=source_id,
                    source_name=source_name,
                    title=full_name,
                    summary=" | ".join(summary_parts),
                    url=url,
                    published_at=normalize_iso(str(repo.get("created_at", "")).strip() or None, fetched_at),
                    fetched_at=fetched_at,
                )
            )
    return items


def _github_headers(auth_env: str | None) -> Dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if auth_env:
        token = os.getenv(auth_env, "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _build_query(source: Dict[str, Any], language: str | None = None, extra: str | None = None) -> str:
    since_days = positive_int(source.get("since_days"), 7)
    min_stars = positive_int(source.get("min_stars"), 80)
    since = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
    parts = [
        f"created:>={since}",
        f"stars:>={min_stars}",
        "archived:false",
        "is:public",
    ]
    if language:
        parts.append(f"language:{language}")
    if extra:
        parts.append(extra)
    return " ".join(parts)


def _iter_query_specs(source: Dict[str, Any]) -> Iterable[tuple[str | None, str | None]]:
    languages = source.get("languages", [])
    extras = source.get("extra_queries", [])
    emitted = False
    if isinstance(languages, list):
        for language in languages:
            text = str(language).strip()
            if text:
                emitted = True
                yield text, None
    if isinstance(extras, list):
        for extra in extras:
            text = str(extra).strip()
            if text:
                emitted = True
                yield None, text
    if not emitted:
        yield None, None

