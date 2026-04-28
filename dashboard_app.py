from __future__ import annotations

from pathlib import Path

try:
    import streamlit as st
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Streamlit is required. Install with: pip install streamlit") from exc

from src.dashboard.view_model import build_dashboard_payload


PRIORITY_COLORS = {
    "Urgent": "#b42318",
    "Important": "#b54708",
    "FYI": "#175cd3",
}


def main() -> None:
    st.set_page_config(page_title="今日 AI 早报", layout="wide")
    _inject_css()

    root = Path(__file__).resolve().parent
    data = build_dashboard_payload(root / "runtime")
    overview = data["overview"]

    st.title("今日 AI 早报")
    st.caption(f"聚焦近 3 天 AI 技术与商业信号 · 更新时间：{data['generated_at']}")

    cols = st.columns(6)
    cols[0].metric("今日采集", overview["collected_total"])
    cols[1].metric("候选池", overview["candidate_count"])
    cols[2].metric("Top10", overview["top10_count"])
    cols[3].metric("AI 精选", "是" if overview.get("ai_selected") else "否")
    cols[4].metric("重要信号", overview["important_count"])
    cols[5].metric("紧急事务", overview.get("urgent_task_count", overview["urgent_mail_count"]))

    left, right = st.columns([2.2, 1], gap="large")
    with left:
        st.subheader("Top10 资讯")
        top_items = data.get("top_items", [])
        if not top_items:
            st.info("暂无 Top10 资讯")
        for item in top_items:
            _render_item(item)

    with right:
        st.subheader("紧急事务")
        mail_alerts = data.get("mail_alerts", [])
        if not mail_alerts:
            st.info("暂无今日紧急事务")
        for item in mail_alerts:
            _render_item(item, compact=True)

        st.subheader("来源统计")
        source_rows = data.get("source_health", [])
        if source_rows:
            st.dataframe(source_rows, hide_index=True, use_container_width=True)
        else:
            st.info("暂无来源统计")


def _render_item(item: dict, compact: bool = False) -> None:
    priority = item.get("priority", "FYI")
    color = PRIORITY_COLORS.get(priority, "#344054")
    rank = item.get("rank", "-")
    title = item.get("title_zh") or item.get("title", "(untitled)")
    title_en = item.get("title_en", "")
    source = item.get("source_name", "-")
    summary = item.get("summary_zh") or item.get("summary", "")
    published_at = item.get("published_at", "")
    url = item.get("url", "")

    st.markdown(
        f"""
        <div class="item">
          <div class="item-head">
            <span class="rank">#{rank}</span>
            <span class="badge" style="background:{color};">{priority}</span>
            <span class="meta">{_escape(source)}</span>
          </div>
          <div class="title">{_escape(title)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if title_en:
        st.caption(f"英文原题：{title_en}")
    if summary:
        st.markdown(f"**主要内容：** {summary}")
    st.caption(f"来源：{source}" + (f" · 发布时间：{published_at}" if published_at else ""))
    if url and not url.startswith("mail:"):
        st.link_button("访问链接", url)
    elif compact:
        st.caption("邮件事项无外部链接")
    st.divider()


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; max-width: 1280px; }
        .item { margin: 0.2rem 0 0.2rem 0; }
        .item-head { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
        .rank { color: #667085; font-size: 0.85rem; }
        .badge { border-radius: 999px; padding: 0.16rem 0.55rem; font-size: 0.76rem; font-weight: 700; color: white; }
        .meta { color: #667085; font-size: 0.84rem; }
        .title { color: #101828; font-size: 1.18rem; font-weight: 700; line-height: 1.38; margin-top: 0.5rem; }
        div[data-testid="stMetric"] { border: 1px solid #eaecf0; padding: 0.75rem; border-radius: 8px; background: #ffffff; }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
