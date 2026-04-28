from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
from typing import Iterable, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import re

from src.models import CollectedItem


PREVIEW_SOURCE_TYPES = {"hackernews_top", "tavily_skill"}


def enrich_link_previews(
    items: Iterable[CollectedItem],
    *,
    enabled: bool = True,
    max_items: int = 10,
    timeout_seconds: int = 8,
) -> List[CollectedItem]:
    output = list(items)
    if not enabled:
        return output

    enriched = 0
    for item in output:
        if enriched >= max_items:
            break
        if item.channel == "mail_alert" or item.source_type not in PREVIEW_SOURCE_TYPES:
            continue
        if not _can_fetch(item.url):
            continue
        preview = fetch_link_preview(item.url, timeout_seconds=timeout_seconds)
        if not preview:
            continue
        item.summary = _merge_preview(item.summary, preview)
        enriched += 1
    return output


def fetch_link_preview(url: str, *, timeout_seconds: int = 8) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "InformationCollector/1.0 (+local briefing link preview)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = str(response.headers.get("Content-Type", "")).lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return ""
            raw = response.read(300_000)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return ""

    html = raw.decode("utf-8", errors="ignore")
    parser = _PreviewParser()
    try:
        parser.feed(html)
    except Exception:
        return ""
    return _clean_preview(parser.best_text())


def _can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _merge_preview(summary: str, preview: str) -> str:
    clean_summary = " ".join((summary or "").split()).strip()
    clean_preview = " ".join((preview or "").split()).strip()
    if not clean_preview:
        return clean_summary
    if not clean_summary:
        return f"Linked page preview. description={clean_preview}"
    return f"Linked page preview. description={clean_preview} | {clean_summary}"


def _clean_preview(text: str, max_chars: int = 700) -> str:
    clean = unescape(text or "")
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


class _PreviewParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_description = ""
        self.og_description = ""
        self.twitter_description = ""
        self.paragraphs: List[str] = []
        self._capture_p = False
        self._current_p: List[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value or "" for name, value in attrs}
        if tag.lower() == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content", "").strip()
            if not content:
                return
            if key == "og:description":
                self.og_description = content
            elif key == "twitter:description":
                self.twitter_description = content
            elif key == "description":
                self.meta_description = content
        elif tag.lower() == "p":
            self._capture_p = True
            self._current_p = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "p" and self._capture_p:
            text = " ".join(self._current_p).strip()
            if len(text) >= 80:
                self.paragraphs.append(text)
            self._capture_p = False
            self._current_p = []

    def handle_data(self, data: str) -> None:
        if self._capture_p:
            text = data.strip()
            if text:
                self._current_p.append(text)

    def best_text(self) -> str:
        return self.og_description or self.twitter_description or self.meta_description or " ".join(self.paragraphs[:2])
