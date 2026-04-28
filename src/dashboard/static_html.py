from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable
from html import escape

from src.dashboard.view_model import build_dashboard_payload


def write_static_dashboard(runtime_dir: Path, output_path: Path) -> Path:
    data = build_dashboard_payload(runtime_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_html(data), encoding="utf-8")
    return output_path


def _render_html(data: Dict[str, Any]) -> str:
    overview = data.get("overview", {})
    top_items = data.get("top_items", [])
    mail_alerts = data.get("mail_alerts", [])
    source_health = data.get("source_health", [])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>今日 AI 早报</title>
  <style>
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; color: #182230; background: #f4f6f8; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 32px 24px; }}
    .hero {{ margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #e4e7ec; }}
    h1 {{ margin: 0 0 7px; font-size: 32px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    .muted {{ color: #667085; font-size: 13px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; margin: 18px 0; }}
    .metric {{ background: white; border: 1px solid #e4e7ec; border-radius: 8px; padding: 13px 14px; }}
    .metric b {{ display: block; font-size: 24px; margin-top: 4px; }}
    .grid {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(300px, 0.9fr); gap: 18px; align-items: start; }}
    .panel {{ background: white; border: 1px solid #e4e7ec; border-radius: 8px; padding: 20px; }}
    .item {{ border-top: 1px solid #eaecf0; padding: 22px 0; }}
    .item:first-child {{ border-top: 0; }}
    .head {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .badge {{ border-radius: 999px; padding: 3px 9px; font-size: 12px; font-weight: 700; border: 1px solid transparent; }}
    .Urgent {{ color: #b42318; background: #fff1f0; border-color: #fecdca; }}
    .Important {{ color: #b54708; background: #fff7ed; border-color: #fed7aa; }}
    .FYI {{ color: #175cd3; background: #eff8ff; border-color: #b2ddff; }}
    .title {{ font-weight: 700; font-size: 20px; margin: 12px 0 6px; line-height: 1.38; }}
    .title-en {{ color: #667085; font-size: 13px; line-height: 1.45; margin-bottom: 12px; }}
    .summary {{ line-height: 1.78; color: #344054; margin: 0 0 12px; font-size: 15px; }}
    .label {{ color: #475467; font-weight: 700; }}
    .row {{ margin-top: 6px; color: #475467; font-size: 13px; }}
    .link {{ display: inline-block; margin-top: 12px; color: #175cd3; font-weight: 700; text-decoration: none; border: 1px solid #d0d5dd; border-radius: 8px; padding: 7px 11px; background: #fff; }}
    .nolink {{ color: #98a2b3; }}
    a {{ color: #175cd3; text-decoration: none; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    td, th {{ border-top: 1px solid #eaecf0; padding: 8px; text-align: left; }}
    @media (max-width: 900px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>今日 AI 早报</h1>
      <div class="muted">聚焦近 3 天 AI 技术与商业信号 · 更新时间：{escape(str(data.get("generated_at", "")))}</div>
    </div>
    <div class="metrics">
      {_metric("今日采集", overview.get("collected_total", 0))}
      {_metric("候选池", overview.get("candidate_count", 0))}
      {_metric("Top10", overview.get("top10_count", 0))}
      {_metric("AI 精选", "是" if overview.get("ai_selected") else "否")}
      {_metric("重要信号", overview.get("important_count", 0))}
      {_metric("紧急事务", overview.get("urgent_task_count", overview.get("urgent_mail_count", 0)))}
    </div>
    <div class="grid">
      <section class="panel">
        <h2>Top10 资讯</h2>
        {_items(top_items, empty_text="暂无 Top10 资讯。")}
      </section>
      <aside>
        <section class="panel">
          <h2>紧急事务</h2>
          {_items(mail_alerts, empty_text="暂无今日紧急事务。")}
        </section>
        <br>
        <section class="panel">
          <h2>来源统计</h2>
          {_sources(source_health)}
        </section>
      </aside>
    </div>
  </div>
</body>
</html>
"""


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span class="muted">{escape(label)}</span><b>{escape(str(value))}</b></div>'


def _items(items: Iterable[Dict[str, Any]], *, empty_text: str) -> str:
    chunks = []
    for item in items:
        priority = escape(str(item.get("priority", "FYI")))
        title = escape(str(item.get("title_zh") or item.get("title", "(untitled)")))
        title_en = escape(str(item.get("title_en", "")))
        source = escape(str(item.get("source_name", "-")))
        summary = escape(str(item.get("summary_zh") or item.get("summary", "")))
        published_at = escape(str(item.get("published_at", "")))
        url = str(item.get("url", "")).strip()
        link = f'<a class="link" href="{escape(url)}" target="_blank">访问链接</a>' if url and not url.startswith("mail:") else '<span class="nolink">邮件事项无外部链接</span>'
        chunks.append(
            f"""<div class="item">
  <div class="head"><span>#{escape(str(item.get("rank", "-")))}</span><span class="badge {priority}">{priority}</span><span class="muted">{source}</span></div>
  <div class="title">{title}</div>
  {f'<div class="title-en">英文原题：{title_en}</div>' if title_en else ''}
  <p class="summary"><span class="label">主要内容：</span>{summary}</p>
  <div class="row"><span class="label">来源：</span>{source}</div>
  <div class="row"><span class="label">发布时间：</span>{published_at or "-"}</div>
  <div>{link}</div>
</div>"""
        )
    return "\n".join(chunks) if chunks else f'<p class="muted">{escape(empty_text)}</p>'


def _sources(rows: Iterable[Dict[str, Any]]) -> str:
    body = "\n".join(
        f"<tr><td>{escape(str(row.get('source_id', '')))}</td><td>{escape(str(row.get('items', 0)))}</td><td>{escape(str(row.get('status', '')))}</td></tr>"
        for row in rows
    )
    return f"<table><thead><tr><th>来源</th><th>数量</th><th>状态</th></tr></thead><tbody>{body}</tbody></table>"
