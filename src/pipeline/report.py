from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
from typing import Iterable

from src.models import CollectedItem, utc_now_iso


def write_items(items: Iterable[CollectedItem], output_path: Path) -> None:
    item_list = list(items)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "count": len(item_list),
        "items": [item.to_dict() for item in item_list],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_source_report(items: Iterable[CollectedItem], output_path: Path) -> None:
    item_list = list(items)
    by_channel = Counter(item.channel for item in item_list)
    by_source = Counter(item.source_id for item in item_list)
    payload = {
        "generated_at": utc_now_iso(),
        "total_items": len(item_list),
        "by_channel": dict(by_channel),
        "by_source": dict(by_source),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_dict_items(items: Iterable[object], output_path: Path) -> None:
    item_list = list(items)
    payload_items = []
    for item in item_list:
        if hasattr(item, "to_dict"):
            payload_items.append(item.to_dict())
        elif isinstance(item, dict):
            payload_items.append(item)
    payload = {
        "count": len(payload_items),
        "items": payload_items,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
