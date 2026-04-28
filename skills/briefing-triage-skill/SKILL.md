---
name: briefing-triage-skill
description: 当 OpenClaw 需要读取 triage_candidates.json，从 25 条候选中打开链接、理解内容、精选 Top10，并写回 ai_selected_top10.json 时使用。
---

# 早报分诊 Skill

当 `runtime/triage_candidates.json` 已经生成后，使用本 Skill 让 OpenClaw/大模型完成最终 Top10 精选和中文早报摘要。

## 职责范围

- 读取 `runtime/triage_candidates.json`。
- 对候选逐条打开链接，理解原文主要内容。
- 从 25 条候选中选出最终 Top10。
- 为每条 Top10 生成中文标题、英文原题、中文主要内容、来源和链接。
- 写回 `runtime/ai_selected_top10.json`。
- 邮件紧急事务单独保留，不参与 Top10。

## Top10 选择逻辑

1. 规则层先生成 `runtime/triage_candidates.json`，数量最多 25 条。
2. OpenClaw 读取这 25 条，优先打开原文链接，不只看标题。
3. 判断 AI 技术价值、商业信号强度、新鲜度和可读性。
4. 最终 Top10 写入 `runtime/ai_selected_top10.json`。
5. 看板优先展示 `ai_selected_top10.json`；如果它不存在，才使用规则版 `top10_items.json` 兜底。

## 写回格式

`runtime/ai_selected_top10.json` 必须是合法 UTF-8 JSON：

```json
{
  "generated_at": "2026-04-28T00:00:00Z",
  "selection_method": "openclaw_ai",
  "items": [
    {
      "rank": 1,
      "item_id": "候选原 item_id",
      "priority": "Important",
      "title_zh": "Microsoft 开源语音 AI 项目 VibeVoice",
      "title_en": "Microsoft VibeVoice: Open-Source Frontier Voice AI",
      "summary_zh": "这篇内容介绍 Microsoft VibeVoice，一个面向语音生成的开源 AI 项目。它提供语音合成相关能力，适合关注多模态交互、语音助手和内容生成工具链的人继续跟踪。",
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
- 安全公告最多选择 1 到 2 条，且必须和 AI、Agent、MCP、OpenClaw、开发工具或基础设施强相关。
- SEC、美联储等宏观/监管信息最多选择 1 条，且必须说明它和 AI 商业环境有关。
- 不要为了凑数选择重复新闻、低质量转载或纯广告页。
- `summary_zh` 必须总结链接对应文章/项目本身的主要内容，不要只写“社区正在讨论”。

## 三级权重说明

- `Urgent`：今日必须处理的信息，或对 AI/业务有明显即时影响的信息。
- `Important`：AI 模型发布、Agent 工具、开源项目、企业采用、融资产品或商业化信号，值得进入今日早报。
- `FYI`：有参考价值但暂时不需要行动的背景信息。
