from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import urlencode

from src.collectors.common import http_json, normalize_iso, positive_int
from src.models import CollectedItem, item_from_fields, utc_now_iso


def fetch_github_advisories(source: Dict[str, Any], *, max_items: int) -> List[CollectedItem]:
    endpoint = str(source.get("endpoint", "")).strip()
    if not endpoint:
        return []

    source_id = str(source.get("id", "github_security_advisories")).strip()
    source_name = str(source.get("name", source_id)).strip()
    auth_env = str(source.get("auth_env", "")).strip() or None
    per_page = positive_int(source.get("per_page"), max_items)
    timeout_seconds = positive_int(source.get("timeout_seconds"), 20)
    fetched_at = utc_now_iso()

    params = {
        "per_page": max(1, min(100, per_page)),
        "sort": "published",
        "direction": "desc",
    }
    payload = http_json(
        f"{endpoint}?{urlencode(params)}",
        headers=_github_headers(auth_env),
        timeout_seconds=timeout_seconds,
    )
    advisories = payload if isinstance(payload, list) else []

    items: List[CollectedItem] = []
    for advisory in advisories:
        if len(items) >= max_items:
            break
        if not isinstance(advisory, dict):
            continue
        url = str(advisory.get("html_url", "")).strip()
        if not url:
            continue

        ghsa_id = str(advisory.get("ghsa_id") or "").strip()
        cve_id = str(advisory.get("cve_id") or "").strip()
        summary = str(advisory.get("summary") or "").strip()
        severity = str(advisory.get("severity") or "").strip()
        title = " | ".join(part for part in (cve_id, ghsa_id, summary[:80]) if part)
        content_parts = [summary] if summary else []
        if severity:
            content_parts.append(f"severity={severity}")
        description = str(advisory.get("description") or "").strip()
        if description:
            content_parts.append(description[:400])

        items.append(
            item_from_fields(
                channel="fixed_platform",
                source_type="github_advisory",
                source_id=source_id,
                source_name=source_name,
                title=title or "GitHub Security Advisory",
                summary=" | ".join(content_parts),
                url=url,
                published_at=normalize_iso(str(advisory.get("published_at", "")).strip() or None, fetched_at),
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

