---
name: tavily-search-wrapper
description: 当 OpenClaw 需要读取 Information Collector 生成的 tavily_search_plan.json，逐个主题调用 tavily-search skill 搜索 AI 最新技术与 AI 商业信号，并把结构化结果写回 tavily_search_results.json 时使用。
---

# Tavily 搜索包装 Skill

本 Skill 的职责是让 OpenClaw 自己完成 Tavily 搜索。不要在 Python 采集器里直接调用 Tavily API，也不要把 Tavily API Key 写入项目代码。

## 输入与输出

输入文件：

```text
runtime/tavily_search_plan.json
```

输出文件：

```text
runtime/tavily_search_results.json
```

如果输入文件不存在，先运行 `information-collector-skill` 或采集流水线，让 Collector 生成搜索计划。

## 执行流程

1. 读取 `runtime/tavily_search_plan.json`。
2. 确认 `enabled` 为 `true`，否则停止搜索并返回“搜索计划未启用”。
3. 遍历 `items`，每个 item 是一个搜索主题。
4. 对每个主题调用 OpenClaw 可用的 `tavily-search` skill。
5. 严格按每日早报口径筛选：只收近 3 天内新闻，不要为了凑数放入旧新闻。
6. 每个主题最多保留 `max_items` 条结果，默认 5 条。
7. 对所有主题结果做 URL 去重，并避免重复上一期早报已经收录的内容。
8. 将结果写入 `runtime/tavily_search_results.json`。
9. 告知用户：需要再次运行 `information-collector-skill`，让搜索结果进入采集、分诊、25 条候选和 Top10。

## 搜索计划字段

每个主题通常包含：

```json
{
  "topic_id": "ai_frontier_technology",
  "topic_name": "AI 前沿技术",
  "query": "latest AI model release multimodal reasoning inference benchmark",
  "domains": ["openai.com", "anthropic.com", "huggingface.co", "arxiv.org"],
  "max_items": 5,
  "recency_days": 3,
  "since_date": "2026-04-25",
  "fallback_recency_days": 3,
  "fallback_since_date": "2026-04-25"
}
```

字段含义：

- `topic_id`：机器字段，必须原样写回结果。
- `topic_name`：中文展示名，用于理解搜索意图。
- `query`：传给 Tavily 的核心搜索词。
- `domains`：优先搜索的网站范围；如果 Tavily 支持 domain/include 参数，传入这些域名；如果不支持，把域名作为搜索提示加入查询。
- `max_items`：该主题最多保留的结果数。
- `recency_days` / `since_date`：每日早报时间窗口，固定近 3 天。
- `fallback_recency_days` / `fallback_since_date`：保持和主窗口一致，不向 3 天外放宽。

## Tavily 查询要求

对每个主题构造搜索请求时，遵守以下规则：

- 这是每日早报，只收最近 3 天内的新信息。
- 优先使用 `since_date` 之后发布或更新的内容。
- 如果某个主题近 3 天不足 `max_items` 条，宁可少于 5 条，也不要收录 3 天以前的信息。
- 不要收录 3 天以前的信息，除非用户明确要求做周报、月报或专题回溯。
- 不要为了凑够 5 条而放入旧新闻；日报的新鲜度优先于数量。
- 避免连续几天重复同一条新闻：如果 URL、标题或核心事件已经出现在上一期 `top10_items.json`、`triage_candidates.json` 或 `tavily_search_results.json` 中，默认跳过。
- 优先选择一手来源、官方博客、论文页、GitHub 项目、可信媒体和高质量社区讨论。
- 避免收录 SEO 聚合页、低质量转载、纯广告页、旧教程、无明确来源的摘要页。
- 搜索结果必须和 AI 技术进展、AI Agent/开源工具、企业采用、融资并购、产品发布或商业化信号有关。
- 每条结果必须有 `title` 和 `url`；缺少这两个字段的结果不要写入。
- 同一个 URL 只保留一次；多个主题命中同一 URL 时，保留更相关的 `topic_id`。

## 去重参考

写回前，尽量读取这些文件作为“已出现内容”的参考：

```text
runtime/top10_items.json
runtime/triage_candidates.json
runtime/tavily_search_results.json
```

如果新结果和这些文件中的内容 URL 相同、标题高度相似，或明显是同一事件的转载，不要写回。每日早报的价值是新鲜度，重复新闻会降低质量。

## 结果写回格式

写入 `runtime/tavily_search_results.json`，必须是合法 UTF-8 JSON：

```json
{
  "generated_at": "2026-04-28T00:00:00Z",
  "source": "openclaw_tavily",
  "items": [
    {
      "topic_id": "ai_frontier_technology",
      "topic_name": "AI 前沿技术",
      "title": "示例标题",
      "url": "https://example.com/article",
      "summary": "1 到 3 句话说明这条信息的核心内容，以及它为什么值得进入 AI 早报候选。",
      "source_name": "Example Source",
      "published_at": "2026-04-28T00:00:00Z",
      "fetched_at": "2026-04-28T00:00:00Z",
      "is_recent": true,
      "relevance_note": "命中 AI 模型发布 / Agent 工具 / 商业采用 / 融资产品信号中的哪一类。"
    }
  ]
}
```

可选字段：

- `channel`：可省略；Collector 会补为 `openclaw_tavily`。
- `source_type`：可省略；Collector 会补为 `tavily_skill`。
- `score`：如果 Tavily 返回相关性分数，可以保留。
- `is_recent`：建议写入；只有符合每日早报时间窗口时才为 `true`。

## 摘要质量

`summary` 不要只复制标题。应包含：

- 发生了什么。
- 涉及哪个公司、项目、模型、产品或开源工具。
- 为什么它对 AI 技术或 AI 商业信号有价值。

示例：

```json
{
  "topic_id": "ai_agent_open_source",
  "topic_name": "AI Agent 与开源工具",
  "title": "Example Agent Framework releases MCP integration",
  "url": "https://example.com/agent-framework-mcp",
  "summary": "Example Agent Framework 发布 MCP 集成，允许开发者把外部工具和企业数据源接入 Agent 工作流。它代表 Agent 工具链继续向标准化插件和企业落地方向推进。",
  "source_name": "Example Blog",
  "published_at": "2026-04-28T00:00:00Z",
  "fetched_at": "2026-04-28T00:00:00Z",
  "relevance_note": "AI Agent 开源工具"
}
```

## 完成后回复

执行完成后，向用户说明：

- 已读取的主题数量。
- 实际写回的结果数量。
- 输出文件路径：`runtime/tavily_search_results.json`。
- 下一步需要再次运行 `information-collector-skill`，把搜索结果纳入分诊和 Top10。

如果没有写回任何结果，说明失败原因，例如：搜索计划为空、Tavily skill 不可用、所有结果被去重或过滤。
