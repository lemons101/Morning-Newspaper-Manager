from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
from typing import Any, Dict
from urllib.request import Request, urlopen


USER_AGENT = "OpenClaw-InformationCollector/0.1"


def positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, parsed)


def http_json(url: str, *, headers: Dict[str, str] | None = None, timeout_seconds: int = 20) -> Any:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def http_text(url: str, *, timeout_seconds: int = 20) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="ignore")


def normalize_iso(value: str | None, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def normalize_rss_datetime(value: str | None, fallback: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return fallback
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return normalize_iso(raw, fallback)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def normalize_unix(value: Any, fallback: str) -> str:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return datetime.fromtimestamp(parsed, tz=timezone.utc).replace(microsecond=0).isoformat()

