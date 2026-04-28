# Information Collector

`Information Collector` 是一个面向 OpenClaw 的信息采集、分诊与可视化早报项目。

它的目标不是“尽可能多地爬数据”，而是把多个可靠渠道里的信息碎片统一采集回来，经过清洗、去重、三级权重判断，最后生成 Top10 资讯和可点击的可视化页面。

## 项目定位

这个项目可以作为一个 OpenClaw Skill 使用：

```text
用户 / OpenClaw
  -> 调用 Information Collector Skill
  -> 自动采集信息
  -> 归类为 Urgent / Important / FYI
  -> 初筛 25 条非邮件候选
  -> 从候选池中选出 Top10
  -> 单独整理邮件告警
  -> 返回 Dashboard 链接
```

## 信息来源

当前项目分成三类信息入口。

### 1. 固定平台来源

这些来源由我们显式配置和维护：

- GitHub 高星项目
- GitHub Security Advisories
- Hacker News Top Stories
- SEC Press Releases RSS
- Federal Reserve RSS

每个来源默认保留 5 条。

### 2. OpenClaw / Tavily 搜索来源

这部分由 OpenClaw 调用 `tavily-search` skill 完成，用于主动搜索配置好的主题，例如：

- AI 前沿技术和模型发布
- AI Agent 与开源工具
- AI 商业化和企业采用
- AI 创业融资与产品发布

实现方式不是在 Python 中直接接 Tavily API，而是通过文件交接：

```text
Collector 生成 runtime/tavily_search_plan.json
OpenClaw 调用 tavily-search skill 搜索
OpenClaw 写回 runtime/tavily_search_results.json
Collector 合并搜索结果并进入分诊
```

### 3. 邮件告警来源

项目支持通过 IMAP / POP3 读取邮箱，并只抽取命中紧急或重要关键词的邮件。

邮件里的未来事项会进入本地事件队列，而不是每天反复扫描旧邮件：

```text
扫描新邮件
  -> 识别会议、截止、审批、提醒等未来事项
  -> 写入 runtime/mail_event_queue.json
  -> 到事件当天再进入 mail_alerts.json
  -> 过期事项自动丢弃
```

邮箱账号和授权码通过 `.env` 配置：

```text
IMAP_USER=your_account@163.com
IMAP_PASS=your_163_authorization_code
```

真实 `.env` 已加入 `.gitignore`，不要提交到代码仓库。

## 三级权重

采集后的信息会被归类为：

- `Urgent`：需要当天处理或升级关注，例如高危安全事故、重大产品风险、关键业务中断、紧急邮件。
- `Important`：值得进入今日早报的信息，例如 AI 前沿技术、模型发布、融资并购、重要开源项目、企业采用信号。
- `FYI`：保留观察的信息，例如普通社区动态、低风险技术资讯。

每条信息会生成：

```text
priority
impact_score
confidence
reasons
suggested_action
short_summary
```

## 初筛与 Top10

普通资讯采用两段式筛选：

1. 规则层先从非邮件信息中选出 25 条 `triage_candidates`，作为给大模型判断的候选池。
2. 大模型后续从这 25 条候选里选择 Top10，并补充更贴近业务语境的理由。

当前版本在大模型接入前，会用同一套规则从 25 条候选里生成 `top10_items.json` 作为兜底结果。

邮件告警不占用 25 条候选名额，也不占用 Top10 名额，会单独输出到 `mail_alerts.json`。

## 运行方式

推荐使用 Skill 入口运行完整流程：

```cmd
cd /d "D:\Openclaw\Information Collector"
conda run -n env1 python -B "skills\information-collector-skill\scripts\run_information_collector.py"
```

运行后会返回类似结果：

```json
{
  "status": "ok",
  "dashboard_url": "http://127.0.0.1:8502",
  "dashboard_file_url": "file:///D:/Openclaw/Information%20Collector/runtime/dashboard.html",
  "overview": {
    "collected_total": 30,
    "top10_count": 10,
    "urgent_count": 5,
    "important_count": 19,
    "mail_alert_count": 0
  }
}
```

## 可视化页面

项目会生成两种可视化入口。

### 动态 Dashboard

```text
http://127.0.0.1:8502
```

由 Streamlit 提供，适合本地实时查看。

### 静态 HTML Dashboard

```text
runtime/dashboard.html
```

静态文件不依赖服务进程，更适合作为 Skill 返回给用户的稳定可点击链接。

## 主要输出文件

运行后会生成：

```text
runtime/collected_items.json
runtime/normalized_items.json
runtime/triage_items.json
runtime/triage_candidates.json
runtime/top10_items.json
runtime/mail_alerts.json
runtime/mail_event_queue.json
runtime/source_report.json
runtime/search_report.json
runtime/tavily_search_plan.json
runtime/tavily_search_results.json
runtime/dashboard.html
```

## 目录结构

```text
Information Collector/
  config/
    app_config.yaml
    sources.yaml
    search_topics.yaml

  src/
    collectors/
      github_high_stars.py
      github_advisories.py
      hackernews.py
      rss.py
      mail.py
      openclaw_tavily.py
    triage/
      rules.py
      ranker.py
    dashboard/
      view_model.py
      server.py
      static_html.py
    pipeline/
      collect.py

  skills/
    information-collector-skill/
    tavily-search-wrapper/
    briefing-triage-skill/

  runtime/
```

## 设计原则

- 优先使用官方 API、RSS、授权服务和 OpenClaw Skill。
- 不做对抗式抓取，不把“绕过反爬”作为系统目标。
- 机器读的字段和目录名保持英文，说明文档和界面文案可以中文化。
- 邮件、固定平台、Tavily 搜索、分诊和展示各自独立，便于后续扩展。
