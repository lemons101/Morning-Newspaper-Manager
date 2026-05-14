---
name: briefing-triage-skill
description: 当 OpenClaw 需要人工复核或重新生成 triage_candidates.json 的 LLM 主编 Top10 结果，并写回 ai_selected_top10.json 时使用。
---

# 早报分诊 Skill

当前自动流水线已经会通过 `ai_triage` 完成候选池摘要、LLM 主编终选 Top10，并写出 `runtime/ai_selected_top10.json`。只有当用户明确要求人工复核、重新排序、手动试 prompt 或修复异常结果时，才使用本 Skill。

## 职责范围

- 读取 `runtime/triage_candidates_enriched.json`，没有时回退到 `runtime/triage_candidates.json`。
- 对候选理解原文主要内容；必要时打开链接补证据。
- 从候选池中选出最终 Top10。
- 为每条 Top10 生成或保留中文标题、英文原题、中文主要内容、来源和链接。
- 写回 `runtime/ai_selected_top10.json`。
- 邮件紧急事务单独保留，不参与 Top10。

## Top10 选择逻辑

1. 规则层负责召回、去重、优先级和兜底；候选池通常约 15 条。
2. 优先读取富化候选池，不只看标题和热度。
3. 判断 AI 主线、新闻价值、可信度、版面多样性和中文主要内容质量。
4. 最终 Top10 写入 `runtime/ai_selected_top10.json`。
5. 看板优先展示 `top10_editorial_ready.json`；如果它不存在，再回退到 `ai_selected_top10.json` 和规则版 `top10_items.json`。

## 写回格式

`runtime/ai_selected_top10.json` 必须是合法 UTF-8 JSON：

```json
{
  "generated_at": "2026-04-28T00:00:00Z",
  "selection_method": "openclaw_ai_editorial_pick_v1",
  "items": [
    {
      "rank": 1,
      "item_id": "候选原 item_id",
      "priority": "Important",
      "title_zh": "Microsoft 开源语音 AI 项目 VibeVoice",
      "title_en": "Microsoft VibeVoice: Open-Source Frontier Voice AI",
      "summary_zh": "这篇内容介绍 Microsoft VibeVoice，一个面向语音生成的开源 AI 项目。它提供语音合成相关能力，适合关注多模态交互、语音助手和内容生成工具链的人继续跟踪。",
      "summary_main": "这篇内容介绍 Microsoft VibeVoice，一个面向语音生成的开源 AI 项目。它提供语音合成相关能力，适合关注多模态交互、语音助手和内容生成工具链的人继续跟踪。",
      "why_it_matters": "语音生成是多模态 AI 落地的重要入口，开源项目会影响开发者工具链和应用原型速度。",
      "key_points": ["VibeVoice 面向语音生成场景。", "项目以开源方式释放。", "适合关注多模态和语音助手的人跟踪。"],
      "summary_en": "可选，保留英文摘要或原始摘要。",
      "source_name": "Hacker News 热门故事",
      "source_type": "hackernews_top",
      "published_at": "2026-04-28T00:00:00Z",
      "url": "https://github.com/microsoft/VibeVoice"
    }
  ]
}
```

## 精选标准

- 优先 AI 模型、AI Agent、开源工具、开发者工具、企业采用、AI 产品发布、融资并购。
- 每日早报只关注近 3 天内的新信息。
- 安全公告通常选择 1 到 2 条；如果候选池里安全风险信息密度明显更高，可以适度增加，但不要挤占全部版面。
- SEC、美联储等宏观/监管信息最多选择 1 条，且必须说明它和 AI 商业环境有关。
- 不要为了凑数选择重复新闻、低质量转载或纯广告页。
- `summary_main` / `summary_zh` 必须总结链接对应文章、项目或公告本身的主要内容，不要只写“社区正在讨论”。英文来源也必须改写成自然中文，允许保留 OpenAI、GitHub、MCP、CVE 等专有名词。

## 三级权重说明

- `Urgent`：今日必须处理的信息，或对 AI/业务有明显即时影响的信息。
- `Important`：AI 模型发布、Agent 工具、开源项目、企业采用、融资产品或商业化信号，值得进入今日早报。
- `FYI`：有参考价值但暂时不需要行动的背景信息。
