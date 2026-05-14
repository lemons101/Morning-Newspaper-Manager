---
name: information-collector-skill
description: 当 OpenClaw 需要采集信息、完成 Urgent/Important/FYI 分诊、生成 LLM 候选池与 Top10 早报数据，并返回可点击的本地看板链接时使用。
---

# 信息采集与早报看板 Skill

当用户希望运行每日信息采集、生成可视化看板、查看 Top10 资讯或检查紧急邮件告警时，使用本 Skill。

## 工作流程

1. 运行信息采集流水线。
2. 生成运行产物：
   - `runtime/collected_items.json`
   - `runtime/triage_items.json`
   - `runtime/triage_candidates.json`
   - `runtime/triage_candidates_enriched.json`
   - `runtime/top10_items.json`，规则兜底版
   - `runtime/ai_selected_top10.json`，LLM 主编终选结果
   - `runtime/top10_editorial_ready.json`，页面展示前的编辑中间层
   - `runtime/mail_alerts.json`
   - `runtime/mail_event_queue.json`
   - `runtime/tavily_search_plan.json`
3. 如果 Streamlit 看板尚未运行，则尝试启动本地看板。
4. 生成稳定的静态 HTML 看板。
5. 返回包含 `dashboard_url` 和 `dashboard_file_url` 的 JSON 摘要。

## Tavily 搜索协作

本 Skill 不直接调用 Tavily API。需要 Tavily 搜索时，先运行本 Skill 生成 `runtime/tavily_search_plan.json`，再让 OpenClaw 使用 `tavily-search-wrapper` 调用 `tavily-search` skill，并把结果写回 `runtime/tavily_search_results.json`。

写回后再次运行本 Skill，搜索结果会自动进入采集、分诊、候选池、LLM 主编终选 Top10 和页面摘要链路。

## Top10 精选协作

当前流水线会自动生成 `runtime/triage_candidates.json`、富化完整候选池，并通过 `ai_triage` 生成 `runtime/ai_selected_top10.json`。其中：

```text
runtime/triage_candidates.json
  -> runtime/triage_candidates_enriched.json
  -> LLM 生成中文 summary_main / why_it_matters / key_points
  -> LLM 主编终选 Top10
  -> runtime/ai_selected_top10.json
  -> runtime/top10_editorial_ready.json
```

看板会优先展示 `runtime/top10_editorial_ready.json`；如果该文件不存在，再依次回退到 `ai_selected_top10.json`、`top10_enriched_items.json` 和规则版 `top10_items.json`。

只有当用户明确要求人工/交互式复核候选池时，才再使用 `briefing-triage-skill`。

## 邮件事件队列

邮件告警不是每天反复扫描所有旧邮件。Collector 会把邮件中的未来会议、截止、审批和提醒写入 `runtime/mail_event_queue.json`，到事件当天再输出到 `runtime/mail_alerts.json`。过期事项会从队列中移除。

## 运行命令

```bash
python skills/information-collector-skill/scripts/run_information_collector.py
```

## 回复要求

- 必须给出可点击的看板链接。
- 必须说明采集总数、候选池数量、Top10 数量、是否已使用 LLM 主编终选、Urgent 数量、Important 数量和紧急事务数量。
- 如果动态看板未能稳定运行，应提示用户使用静态 HTML 看板链接。
