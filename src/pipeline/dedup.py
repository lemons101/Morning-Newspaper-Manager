from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from src.models import CollectedItem


def deduplicate_items(items: Iterable[CollectedItem]) -> List[CollectedItem]:
    seen: Set[Tuple[str, str]] = set()
    output: List[CollectedItem] = []
    for item in items:
        key = (item.url.strip().lower(), item.title.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output

