from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from src.collectors.common import positive_int
from src.collectors.github_advisories import fetch_github_advisories
from src.collectors.github_high_stars import fetch_github_high_stars
from src.collectors.hackernews import fetch_hackernews_top
from src.collectors.mail import fetch_mail_alerts
from src.collectors.rss import fetch_rss
from src.models import CollectedItem


Fetcher = Callable[[Dict[str, Any]], List[CollectedItem]]


def build_fixed_source_plan(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources = config.get("fixed_sources", [])
    if not isinstance(sources, list):
        return []
    return [source for source in sources if isinstance(source, dict) and source.get("enabled", False)]


def collect_fixed_platforms(
    config: Dict[str, Any],
    *,
    root: Path | None = None,
    runtime_config: Dict[str, Any] | None = None,
) -> List[CollectedItem]:
    items: List[CollectedItem] = []
    for source in build_fixed_source_plan(config):
        source_id = str(source.get("id", "")).strip() or "(unknown)"
        source_type = str(source.get("type", "")).strip()
        print(f"[采集开始] fixed source id={source_id} type={source_type}")
        fetcher = _fetcher_for_type(source_type, root=root, runtime_config=runtime_config or {})
        if fetcher is None:
            print(f"[WARN] unsupported fixed source type={source_type} id={source.get('id')}")
            continue
        try:
            fetched = fetcher(source)
            items.extend(fetched)
            print(f"[采集完成] fixed source id={source_id} type={source_type} items={len(fetched)}")
        except Exception as exc:
            print(f"[WARN] fixed source failed id={source.get('id')} type={source_type}: {exc}")
    return items


def _fetcher_for_type(
    source_type: str,
    *,
    root: Path | None = None,
    runtime_config: Dict[str, Any] | None = None,
) -> Fetcher | None:
    if source_type == "github_high_stars":
        return lambda source: fetch_github_high_stars(
            source,
            max_items=positive_int(source.get("max_items"), 5),
        )
    if source_type == "github_advisory":
        return lambda source: fetch_github_advisories(
            source,
            max_items=positive_int(source.get("max_items"), 5),
        )
    if source_type == "hackernews_top":
        return lambda source: fetch_hackernews_top(
            source,
            max_items=positive_int(source.get("max_items"), 5),
        )
    if source_type == "rss":
        return lambda source: fetch_rss(
            source,
            max_items=positive_int(source.get("max_items"), 5),
        )
    if source_type == "mail_alerts":
        return lambda source: fetch_mail_alerts(
            source,
            max_items=positive_int(source.get("max_items"), 5),
            root=root,
            runtime_config=runtime_config or {},
        )
    return None
