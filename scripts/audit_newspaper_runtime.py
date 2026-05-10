from __future__ import annotations

import json
import re
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
    'GitHub Reviewed',
    'Published May',
    'Updated May',
    'Dependabot alerts',
    'Navigation Menu',
    'Sign In Subscribe',
    'Posts RSS',
    'RSS Contact',
]


def _too_much_english(text: str) -> bool:
    words = re.findall(r'[A-Za-z]{4,}', str(text or ''))
    return len(words) >= 8


def _title_not_localized(title: str) -> bool:
    title = str(title or '').strip()
    zh_chars = len(re.findall(r'[\u4e00-\u9fff]', title))
    ascii_words = re.findall(r'[A-Za-z]{3,}', title)
    return zh_chars < 4 and len(ascii_words) >= 3


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _items(path: Path) -> List[Dict[str, Any]]:
    payload = _read_json(path)
    items = payload.get('items', []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


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
    if 'hacker news 热门内容围绕一个正在被开发者集中讨论的技术主题展开' in text.lower():
        return 'generic_hn_fallback'
    if re.search(r'我用它一个月涨粉\s*100w', text, flags=re.I):
        return 'marketing_dump'
    if _too_much_english(text):
        return 'too_much_english'
    return None


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/root/projects/Morning-Newspaper-Manager')
    runtime = root / 'runtime'
    editorial = _items(runtime / 'top10_editorial_ready.json')
    final_payload = _read_json(runtime / 'final_newspaper.json')
    html_path = runtime / 'dashboard.html'
    problems: List[str] = []

    if len(editorial) != 10:
        problems.append(f'top10_editorial_ready items={len(editorial)} expected=10')

    final_items = final_payload.get('items', []) if isinstance(final_payload.get('items', []), list) else []
    if len(final_items) != 10:
        problems.append(f'final_newspaper items={len(final_items)} expected=10')

    if not html_path.exists():
        problems.append('dashboard.html missing')
    else:
        html = html_path.read_text(encoding='utf-8', errors='ignore')
        if '紧急会议通知' in html:
            problems.append('stale_meeting_alert_visible_in_dashboard')

    for idx, item in enumerate(editorial, 1):
        title = str(item.get('title_zh') or item.get('card_title') or item.get('title') or '').strip()
        summary = str(item.get('summary_main') or item.get('card_summary') or '').strip()
        issue = _bad_summary(summary)
        if issue:
            problems.append(f'#{idx} {title}: {issue}')
        if _title_not_localized(title):
            problems.append(f'#{idx} {title}: title_not_localized')

    if html_path.exists():
        html = html_path.read_text(encoding='utf-8', errors='ignore')
        if '英文原题:' in html:
            problems.append('dashboard_shows_english_original_title')

    if problems:
        print('[FAIL] newspaper runtime audit failed')
        for p in problems:
            print('-', p)
        return 1

    print('[OK] newspaper runtime audit passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
