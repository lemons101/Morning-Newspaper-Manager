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
    headline = data.get("headline", "今日 AI 早报")
    lead = data.get("lead", [])
    top_stories = data.get("top_stories", [])
    other_signals = data.get("other_signals", [])
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
    body {{ margin: 0; font-family: Inter, Arial, "Microsoft YaHei", sans-serif; color: #182230; background: linear-gradient(180deg, #f8fafc 0%, #f3f6fb 100%); }}
    .wrap {{ max-width: 1180px; margin: 0 auto; padding: 36px 24px 48px; }}
    .hero {{ margin-bottom: 20px; padding: 24px 24px 18px; border: 1px solid #e4e7ec; border-radius: 18px; background: linear-gradient(135deg, #ffffff 0%, #f7fbff 100%); box-shadow: 0 10px 30px rgba(16,24,40,0.06); }}
    .leadbox {{ margin-top: 16px; max-width: 980px; }}
    .leadtitle {{ font-size: 13px; font-weight: 800; color: #175cd3; margin-bottom: 10px; letter-spacing: .04em; text-transform: uppercase; }}
    .leadgrid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .leadcard {{ background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%); border: 1px solid #dbe7ff; border-radius: 14px; padding: 14px 14px 13px; box-shadow: 0 4px 14px rgba(23,92,211,0.06); }}
    .leadcard-title {{ font-size: 15px; font-weight: 800; color: #182230; margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }}
    .leadcard-summary {{ margin: 0; color: #475467; font-size: 14px; line-height: 1.75; }}
    h1 {{ margin: 0 0 8px; font-size: 34px; letter-spacing: -0.02em; }}
    h2 {{ margin: 0 0 16px; font-size: 21px; letter-spacing: -0.01em; }}
    .muted {{ color: #667085; font-size: 13px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 20px 0; }}
    .metric {{ background: rgba(255,255,255,0.94); border: 1px solid #e4e7ec; border-radius: 14px; padding: 14px 15px; box-shadow: 0 4px 14px rgba(16,24,40,0.04); }}
    .metric b {{ display: block; font-size: 24px; margin-top: 6px; }}
    .grid {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(300px, 0.92fr); gap: 20px; align-items: start; }}
    .panel {{ background: rgba(255,255,255,0.97); border: 1px solid #e4e7ec; border-radius: 18px; padding: 22px; box-shadow: 0 8px 24px rgba(16,24,40,0.05); }}
    .item {{ border-top: 1px solid #eef2f6; padding: 22px 0; }}
    .item:first-child {{ border-top: 0; padding-top: 8px; }}
    .head {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .badge {{ border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; border: 1px solid transparent; }}
    .Urgent {{ color: #b42318; background: #fff1f0; border-color: #fecdca; }}
    .Important {{ color: #b54708; background: #fff7ed; border-color: #fed7aa; }}
    .FYI {{ color: #175cd3; background: #eff8ff; border-color: #b2ddff; }}
    .title {{ font-weight: 800; font-size: 21px; margin: 12px 0 8px; line-height: 1.4; letter-spacing: -0.01em; }}
    .title-en {{ color: #98a2b3; font-size: 12px; line-height: 1.5; margin-bottom: 12px; }}
    .summary {{ line-height: 1.82; color: #344054; margin: 0 0 14px; font-size: 15px; }}
    .label {{ color: #344054; font-weight: 700; }}
    .points {{ margin: 10px 0 14px 0; padding-left: 20px; color: #475467; }}
    .points li {{ margin: 6px 0; line-height: 1.7; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 12px 18px; margin-top: 10px; }}
    .row {{ color: #667085; font-size: 13px; background: #f8fafc; border: 1px solid #eef2f6; border-radius: 999px; padding: 6px 10px; }}
    .link {{ display: inline-block; margin-top: 14px; color: #175cd3; font-weight: 700; text-decoration: none; border: 1px solid #c7d7fe; border-radius: 10px; padding: 8px 12px; background: #f5f8ff; }}
    .link:hover {{ background: #eaf1ff; }}
    .nolink {{ color: #98a2b3; }}
    a {{ color: #175cd3; text-decoration: none; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    td, th {{ border-top: 1px solid #eaecf0; padding: 8px; text-align: left; }}
    @media (max-width: 900px) {{ .metrics {{ grid-template-columns: repeat(2, 1fr); }} .grid {{ grid-template-columns: 1fr; }} .leadgrid {{ grid-template-columns: 1fr; }} .hero {{ padding: 20px 18px 16px; }} .panel {{ padding: 18px; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>{escape(str(headline))}</h1>
      <div class="muted">聚焦近 3 天 AI 技术与商业信号 · 更新时间：{escape(str(data.get("generated_at", "")))}</div>
      {_lead_cards(lead)}
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
        <h2>Top10</h2>
        {_items(top_items, empty_text="暂无 Top10 内容。")} 
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


def _lead_cards(items: Iterable[Dict[str, Any]]) -> str:
    cards = []
    for item in items:
        icon = escape(str(item.get("icon", "✨")))
        title = escape(str(item.get("title", "")))
        summary = escape(str(item.get("summary", "")))
        cards.append(
            f'<div class="leadcard"><div class="leadcard-title">{icon} {title}</div><p class="leadcard-summary">{summary}</p></div>'
        )
    if not cards:
        return ''
    return f'<div class="leadbox"><div class="leadtitle">今日看点</div><div class="leadgrid">{"".join(cards)}</div></div>'


def _items(items: Iterable[Dict[str, Any]], *, empty_text: str) -> str:
    chunks = []
    for item in items:
        priority = escape(str(item.get("priority", "FYI")))
        icon = escape(str(item.get("topic_icon", "✨")))
        title = escape(str(item.get("title_zh") or item.get("title", "(untitled)")))
        title_en = escape(str(item.get("title_en", "")))
        source = escape(str(item.get("source_name", "-")))
        summary = escape(str(item.get("summary_zh") or item.get("summary", "")))
        published_at = escape(str(item.get("published_at", "")))
        key_points = item.get("key_points") or []
        if not isinstance(key_points, list):
            key_points = []
        point_items = ''.join(f'<li>{escape(str(point))}</li>' for point in key_points[:3] if str(point).strip())
        points_html = f'<ul class="points">{point_items}</ul>' if point_items else ''
        url = str(item.get("url", "")).strip()
        link = f'<a class="link" href="{escape(url)}" target="_blank">访问链接</a>' if url and not url.startswith("mail:") else '<span class="nolink">邮件事项无外部链接</span>'
        chunks.append(
            f"""<div class="item">
  <div class="head"><span>#{escape(str(item.get("rank", "-")))}</span><span class="badge {priority}">{priority}</span><span class="muted">{source}</span></div>
  <div class="title">{icon} {title}</div>
  <p class="summary"><span class="label">主要内容:</span>{summary}</p>
  {points_html}
  <div class="meta">
    <div class="row"><span class="label">来源</span> · {source}</div>
    <div class="row"><span class="label">发布时间</span> · {published_at or "-"}</div>
  </div>
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
