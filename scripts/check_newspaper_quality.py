from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BAD_PREFIXES = [
    '这条内容值得关注',
    '这条内容当前更像一个社区讨论入口',
    '它属于官方/监管信号',
    '这条内容对应的是一则需要尽快核查影响面的安全公告',
    '链接内容主要围绕',
    '这是一条官方发布，主要内容是：',
    '这条内容当前更适合先概括',
    '这是一个近期升温的开源项目',
    '这是一则安全公告',
    '当前可直接确认的正文信息还有限',
]

BAD_CONTAINS = [
    '它之所以能进今天的候选',
    '适合作为补充阅读而不是主线内容',
    '帮助团队快速形成核查动作',
    '为什么会被开发者集中讨论',
    '保守概括',
]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _bad_summary(text: str) -> str | None:
    text = str(text or '').strip()
    if not text:
        return 'empty'
    for prefix in BAD_PREFIXES:
        if text.startswith(prefix):
            return f'bad_prefix:{prefix}'
    for marker in BAD_CONTAINS:
        if marker in text:
            return f'bad_contains:{marker}'
    return None


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/root/projects/Morning-Newspaper-Manager')
    runtime = root / 'runtime'
    payload = _read_json(runtime / 'top10_editorial_ready.json')
    items: List[Dict[str, Any]] = payload.get('items', []) if isinstance(payload.get('items', []), list) else []

    problems: List[str] = []
    if len(items) != 10:
        problems.append(f'top10_count={len(items)} expected=10')

    for idx, item in enumerate(items, 1):
        title = str(item.get('title') or item.get('card_title') or '').strip()
        summary = str(item.get('summary_main') or item.get('card_summary') or item.get('editorial_summary_hint') or '').strip()
        issue = _bad_summary(summary)
        if issue:
            problems.append(f'#{idx} {title}: {issue}')

    html_path = runtime / 'dashboard.html'
    if not html_path.exists():
        problems.append('dashboard.html missing')

    if problems:
        print('[FAIL] newspaper quality check failed')
        for p in problems:
            print('-', p)
        return 1

    print('[OK] newspaper quality check passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
