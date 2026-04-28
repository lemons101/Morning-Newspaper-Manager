# 信息源策略

## 采集目标

采集对 AI 技术判断、AI 产品趋势、AI 商业化和企业采用有价值的最新信息碎片，并保留来源、链接、主题和采集通道，方便后续审计和复盘。

## 选源原则

- 优先使用官方 API、RSS 和授权搜索服务。
- 信息源保持小而清晰，先保证质量，再逐步扩展。
- 每个来源设置数量上限，避免单一平台挤占早报版面。
- 保留来源追踪字段：来源、URL、查询主题和采集通道。
- Tavily 作为 OpenClaw 的主动搜索工具使用，不作为隐藏爬虫使用。

## 当前信息源地图

| 通道 | 来源 | 用途 | 上限 |
|---|---|---:|---:|
| 固定平台 | GitHub Search API | 发现快速增长的开源项目和 AI 工具信号 | 5 |
| 固定平台 | GitHub Security Advisories API | 发现开源依赖和安全漏洞风险 | 5 |
| 固定平台 | Hacker News API | 发现工程、创业和技术社区趋势 | 5 |
| 固定平台 | SEC RSS | 获取监管、上市公司和合规风险信号 | 5 |
| 固定平台 | Federal Reserve RSS | 作为背景信号，辅助判断 AI 商业化所处的市场环境 | 5 |
| 内部告警 | 邮箱 IMAP/POP3 | 获取订阅邮件、高管邮件和紧急运营提醒 | 5 |
| OpenClaw 搜索 | tavily-search skill | Collector 生成搜索计划，OpenClaw 自己调用 Tavily 搜索 AI 技术和商业信号，再写回结果 | 每主题 5 条 |

## Tavily 域名提示

AI 商业化和企业采用信息优先关注：

- `reuters.com`
- `bloomberg.com`
- `cnbc.com`
- `ft.com`
- `wsj.com`
- `marketwatch.com`
- `finance.yahoo.com`

开源社区信息优先关注：

- `github.com`
- `news.ycombinator.com`

AI 前沿技术信息优先关注：

- `openai.com`
- `anthropic.com`
- `deepmind.google`
- `ai.meta.com`
- `huggingface.co`
- `arxiv.org`

## 邮箱信号

邮箱采集被视为内部告警通道。系统会扫描最近邮件，只输出命中紧急或重要关键词的邮件。

凭据来自环境变量或 `.env`：

- `IMAP_USER`
- `IMAP_PASS`

如果 IMAP 被邮箱服务商拦截，并且配置启用了 POP3 fallback，系统会尝试使用相同凭据走 POP3。
