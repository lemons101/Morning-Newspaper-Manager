from __future__ import annotations

from pathlib import Path
import os
from typing import Any, Dict

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from exc


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def load_project_config(root: Path) -> Dict[str, Any]:
    load_dotenv(root / ".env")
    return {
        "app": read_yaml(root / "config" / "app_config.yaml"),
        "sources": read_yaml(root / "config" / "sources.yaml"),
        "search_topics": read_yaml(root / "config" / "search_topics.yaml"),
    }
