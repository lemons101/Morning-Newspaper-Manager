---
name: information-collector-skill
description: 当 OpenClaw 需要采集信息、完成 Urgent/Important/FYI 分诊、生成 Top10 早报数据，并返回可点击的本地看板链接时使用。
---

# 信息采集与早报看板 Skill

当用户希望运行每日信息采集、生成可视化看板、查看 Top10 资讯或检查紧急邮件告警时，使用本 Skill。

## 工作流程

1. 运行信息采集流水线。
2. 生成运行产物：
   - `runtime/collected_items.json`
   - `runtime/triage_items.json`
   - `runtime/triage_candidates.json`
   - `runtime/top10_items.json`
   - `runtime/ai_selected_top10.json`，如果 OpenClaw 已完成精选
   - `runtime/mail_alerts.json`
   - `runtime/mail_event_queue.json`
   - `runtime/tavily_search_plan.json`
3. 如果 Streamlit 看板尚未运行，则尝试启动本地看板。
4. 生成稳定的静态 HTML 看板。
5. 返回包含 `dashboard_url` 和 `dashboard_file_url` 的 JSON 摘要。

## Tavily 搜索协作

本 Skill 不直接调用 Tavily API。需要 Tavily 搜索时，先运行本 Skill 生成 `runtime/tavily_search_plan.json`，再让 OpenClaw 使用 `tavily-search-wrapper` 调用 `tavily-search` skill，并把结果写回 `runtime/tavily_search_results.json`。

写回后再次运行本 Skill，搜索结果会自动进入采集、分诊、25 条候选和 Top10。

## Top10 精选协作

本 Skill 的规则层会生成 `runtime/triage_candidates.json` 和兜底版 `runtime/top10_items.json`。最终日报建议再使用 `briefing-triage-skill`：

```text
runtime/triage_candidates.json
  -> OpenClaw 打开链接、理解内容、精选 Top10
  -> runtime/ai_selected_top10.json
```

看板会优先展示 `runtime/ai_selected_top10.json`；如果该文件不存在，才展示规则版 `runtime/top10_items.json`。

## 邮件事件队列

邮件告警不是每天反复扫描所有旧邮件。Collector 会把邮件中的未来会议、截止、审批和提醒写入 `runtime/mail_event_queue.json`，到事件当天再输出到 `runtime/mail_alerts.json`。过期事项会从队列中移除。

## 运行命令

```bash
python skills/information-collector-skill/scripts/run_information_collector.py
```

## 回复要求

- 必须给出可点击的看板链接。
- 必须说明采集总数、初筛候选数量、Top10 数量、是否已使用 AI 精选、Urgent 数量、Important 数量和紧急事务数量。
- 如果动态看板未能稳定运行，应提示用户使用静态 HTML 看板链接。
