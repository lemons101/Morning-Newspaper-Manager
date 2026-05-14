from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.fixed_platforms import build_fixed_source_plan, collect_fixed_platforms
from src.collectors.openclaw_tavily import build_tavily_topic_plan, collect_openclaw_tavily
from src.config import load_project_config
from src.pipeline.ai_triage import run_ai_triage
from src.pipeline.content_enrich import enrich_candidates_with_content
from src.pipeline.dedup import deduplicate_items
from src.pipeline.link_preview import enrich_link_previews
from src.pipeline.llm_candidate_triage import run_llm_candidate_triage, select_triage_candidates_by_llm
from src.pipeline.newspaper_writer import run_newspaper_writer
from src.pipeline.report import write_dict_items, write_items, write_source_report
from src.triage.ranker import select_mail_alerts
from src.triage.rules import triage_items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行 Information Collector 信息采集流程。")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.project_root).resolve()
    config = load_project_config(root)

    fixed_plan = build_fixed_source_plan(config["sources"])
    tavily_plan = build_tavily_topic_plan(config["search_topics"])

    print(f"[计划] 固定来源数量={len(fixed_plan)}")
    for source in fixed_plan:
        print(f"[计划] 固定来源 id={source.get('id')} type={source.get('type')} 上限={source.get('max_items')}")

    print(f"[计划] Tavily 搜索主题数量={len(tavily_plan)}")
    for topic in tavily_plan:
        topic_name = topic.get("name") or topic.get("id")
        print(f"[计划] Tavily 主题 {topic_name} 上限=5 查询={topic.get('query')}")

    if args.plan_only:
        return

    items = []
    runtime_cfg = config["app"].get("runtime", {})
    items.extend(collect_fixed_platforms(config["sources"], root=root, runtime_config=runtime_cfg))
    items.extend(collect_openclaw_tavily(config["search_topics"], root=root, runtime_config=runtime_cfg))
    print(f"[阶段完成] 原始采集 items={len(items)}")
    enrichment_cfg = config["app"].get("enrichment", {})
    if not isinstance(enrichment_cfg, dict):
        enrichment_cfg = {}
    print("[阶段开始] link previews")
    items = enrich_link_previews(
        items,
        enabled=bool(enrichment_cfg.get("enabled", True)),
        max_items=int(enrichment_cfg.get("max_link_previews", 10) or 10),
        timeout_seconds=int(enrichment_cfg.get("timeout_seconds", 8) or 8),
    )
    print(f"[阶段完成] link previews items={len(items)}")
    deduped = deduplicate_items(items)
    print(f"[阶段完成] dedup items={len(deduped)}")
    triaged = triage_items(deduped)
    print(f"[阶段完成] triage items={len(triaged)}")
    triage_cfg = config["app"].get("triage", {})
    top_n = int(triage_cfg.get("top_n", 10)) if isinstance(triage_cfg, dict) else 10
    candidate_limit = int(triage_cfg.get("candidate_limit", 15)) if isinstance(triage_cfg, dict) else 15
    output_dir = root / str(runtime_cfg.get("output_dir", "runtime"))
    write_dict_items(triaged, output_dir / str(runtime_cfg.get("triage_items_file", "triage_items.json")))
    print("[阶段开始] llm_candidate_triage")
    llm_triage_path = run_llm_candidate_triage(root)
    llm_triaged_payload = json.loads(llm_triage_path.read_text(encoding='utf-8')) if llm_triage_path.exists() else {}
    llm_triaged_items = llm_triaged_payload.get('items', []) if isinstance(llm_triaged_payload, dict) else []
    triage_candidates = select_triage_candidates_by_llm(llm_triaged_items, limit=candidate_limit)
    print(f"[阶段完成] llm_candidate_triage items={len(llm_triaged_items)}")
    print(f"[阶段完成] triage_candidates items={len(triage_candidates)}")
    print("[阶段开始] enrich triage_candidates")
    enriched_candidates = enrich_candidates_with_content(
        [dict(item) for item in triage_candidates],
        root=root,
        enabled=True,
    )
    print(f"[阶段完成] enrich triage_candidates items={len(enriched_candidates)}")
    top_items = triage_candidates[:max(1, top_n)]
    enriched_top_items = enriched_candidates[:max(1, top_n)]
    print(f"[阶段完成] provisional_top_items items={len(top_items)}")
    mail_alerts = select_mail_alerts(triaged)
    print(f"[阶段完成] mail_alerts items={len(mail_alerts)}")

    print(f"[阶段开始] write outputs dir={output_dir}")
    write_items(deduped, output_dir / str(runtime_cfg.get("collected_items_file", "collected_items.json")))
    write_items(deduped, output_dir / str(runtime_cfg.get("normalized_items_file", "normalized_items.json")))
    write_dict_items(triaged, output_dir / str(runtime_cfg.get("triage_items_file", "triage_items.json")))
    if llm_triage_path.exists():
        (output_dir / 'triage_items_llm_scored.json').write_text(llm_triage_path.read_text(encoding='utf-8'), encoding='utf-8')
    write_dict_items(triage_candidates, output_dir / str(runtime_cfg.get("triage_candidates_file", "triage_candidates.json")))
    write_dict_items(enriched_candidates, output_dir / "triage_candidates_enriched.json")
    write_dict_items(top_items, output_dir / str(runtime_cfg.get("top10_items_file", "top10_items.json")))
    write_dict_items(enriched_top_items, output_dir / "top10_enriched_items.json")
    write_dict_items(mail_alerts, output_dir / str(runtime_cfg.get("mail_alerts_file", "mail_alerts.json")))
    write_source_report(deduped, output_dir / str(runtime_cfg.get("source_report_file", "source_report.json")))
    write_source_report(deduped, output_dir / str(runtime_cfg.get("search_report_file", "search_report.json")))
    print("[阶段完成] write outputs")
    if bool(config.get("app", {}).get("openclaw", {}).get("ai_triage_enabled", True)):
        print("[阶段开始] ai_triage")
        run_ai_triage(root)
        print("[阶段完成] ai_triage")
        print("[阶段开始] newspaper_writer / editorial_ready")
        run_newspaper_writer(root)
        print("[阶段完成] newspaper_writer / editorial_ready")
    print(
        f"[完成] 采集={len(deduped)} 分诊={len(triaged)} "
        f"初筛候选={len(triage_candidates)} Top10={len(top_items)} "
        f"邮件告警={len(mail_alerts)} 输出目录={output_dir}"
    )


if __name__ == "__main__":
    main()
