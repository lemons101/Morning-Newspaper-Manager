from __future__ import annotations

from pathlib import Path
import os


def resolve_project_root(cli_arg: str | None = None) -> Path:
    if cli_arg:
        return Path(cli_arg).expanduser().resolve()
    env_root = os.environ.get('MORNING_NEWSPAPER_PROJECT_ROOT', '').strip()
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[1]
