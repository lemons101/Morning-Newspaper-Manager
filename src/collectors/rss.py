from __future__ import annotations

from typing import Any, Dict, List
import xml.etree.ElementTree as ET

from src.collectors.common import http_text, normalize_rss_datetime
from src.models import CollectedItem, item_from_fields, utc_now_iso


def fetch_rss(source: Dict[str, Any], *, max_items: int) -> List[CollectedItem]:
    url = str(source.get("url", "")).strip()
    if not url:
        return []

    source_id = str(source.get("id", "rss")).strip()
    source_name = str(source.get("name", source_id)).strip()
    fetched_at = utc_now_iso()
    text = http_text(url, timeout_seconds=20)
    root = ET.fromstring(text)
    entries = root.findall(".//item")
    if not entries:
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    items: List[CollectedItem] = []
    for entry in entries[:max_items]:
        title = _xml_text(entry.find("title")) or _xml_text(entry.find("{http://www.w3.org/2005/Atom}title"))
        link = _xml_text(entry.find("link"))
        if not link:
            atom_link = entry.find("{http://www.w3.org/2005/Atom}link")
            link = str(atom_link.get("href", "")).strip() if atom_link is not None else ""
        summary = (
            _xml_text(entry.find("description"))
            or _xml_text(entry.find("summary"))
            or _xml_text(entry.find("{http://www.w3.org/2005/Atom}summary"))
        )
        published_raw = (
            _xml_text(entry.find("pubDate"))
            or _xml_text(entry.find("published"))
            or _xml_text(entry.find("{http://www.w3.org/2005/Atom}published"))
            or _xml_text(entry.find("{http://www.w3.org/2005/Atom}updated"))
        )
        if not title and not link:
            continue
        items.append(
            item_from_fields(
                channel="fixed_platform",
                source_type="rss",
                source_id=source_id,
                source_name=source_name,
                title=title or "(untitled)",
                summary=summary,
                url=link,
                published_at=normalize_rss_datetime(published_raw, fetched_at),
                fetched_at=fetched_at,
            )
        )
    return items


def _xml_text(element: ET.Element | None, fallback: str = "") -> str:
    if element is None or element.text is None:
        return fallback
    return element.text.strip()

