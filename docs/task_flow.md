# Morning-Newspaper-Manager 任务流

## 目标

把 AI 技术、AI Agent、开源工具、安全与商业信号，稳定地从多来源采集回来，经过分诊、候选池收敛、Top10 选择、正文增强和编辑整理，最终输出成可分享的中文晨报页面。

---

## 当前真实链路

```text
来源采集
  -> 去重与 triage
  -> triage_candidates
  -> top10_items
  -> top10_enriched_items
  -> top10_editorial_ready
  -> final_newspaper
  -> dashboard.html
  -> 8510 固定链接
  -> 每日自动更新 / 每日推送
```

---

## 分层理解

### 1. 采集层
负责把信息采回来并统一成结构化条目。

包括：

- GitHub 高星项目
- GitHub 安全公告
- Hacker News 热门故事
- RSS 来源
- 邮件告警
- Tavily 搜索计划 / 搜索结果回填

输出重点：

- `collected_items.json`
- `normalized_items.json`

### 2. 分诊层
负责把信息从“原始条目”收敛成更值得看的候选。

包括：

- 去重
- triage（Urgent / Important / FYI）
- 候选池选择
- Top10 选择

输出重点：

- `triage_items.json`
- `triage_candidates.json`
- `top10_items.json`

### 3. 内容增强层
负责把 Top10 从短条目变成更接近可写稿素材的内容。

包括：

- 正文抓取
- link preview
- 内容清洗
- 编辑提示生成

输出重点：

- `top10_enriched_items.json`
- `top10_editorial_ready.json`

### 4. 成稿与展示层
负责把编辑素材包变成最终对用户可见的晨报。

包括：

- 生成 `final_newspaper.json`
- 生成 `final_newspaper.md`
- 生成 `runtime/dashboard.html`
- 静态页面展示
- 8510 固定访问链接

---

## 详细任务流

### Step 1：读取配置
读取：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### Step 2：固定来源采集
拉取配置好的固定平台来源。

### Step 3：Tavily 搜索计划与结果回填
Collector 本身不直接调用 Tavily API，而是：

1. 生成 `runtime/tavily_search_plan.json`
2. 由 OpenClaw / skill 完成搜索
3. 写回 `runtime/tavily_search_results.json`
4. Collector 再合并回主流程

### Step 4：原始条目合并
把固定来源、搜索结果、邮件信号汇总成统一条目流。

### Step 5：link preview 与基础增强
为部分条目补充页面基础信息。

### Step 6：去重
根据 URL、标题等进行去重。

### Step 7：triage
把条目分成：

- `Urgent`
- `Important`
- `FYI`

### Step 8：候选池选择
从非邮件条目中选出 `triage_candidates`。

### Step 9：Top10 生成
基于候选池生成 `top10_items.json`。

### Step 10：正文增强
对 Top10 做正文抓取、清洗和内容增强。

输出：

- `top10_enriched_items.json`

### Step 11：editorial-ready 生成
将增强后的内容进一步整理成适合成稿和页面展示的素材包。

输出：

- `top10_editorial_ready.json`

这是当前最关键的中间层。

### Step 12：最终晨报生成
从 editorial-ready 素材生成：

- `final_newspaper.json`
- `final_newspaper.md`
- `runtime/dashboard.html`

### Step 13：展示与分享
通过固定链接访问：

- `http://101.47.152.44:8510/dashboard.html`

---

## 自动化链路

### 每日 08:00
自动重跑晨报链，更新当天 HTML。

### 每日 08:05
自动推送：

- 今日晨报已更新
- 3 条今日看点
- 固定链接

---

## 当前关键设计判断

### 1. `top10_editorial_ready.json` 是中间核心
它是连接采集结果和成品展示的桥。

### 2. 静态 HTML 是当前主交付物
如果目标是“让用户看晨报”，当前优先交付：

- `runtime/dashboard.html`

### 3. 当前不是历史归档系统
当前链路会按天覆盖当天内容，而不是保留每日历史快照。

---

## 推荐排查顺序

如果页面内容不对，建议按顺序排查：

1. `top10_items.json`
2. `top10_enriched_items.json`
3. `top10_editorial_ready.json`
4. `final_newspaper.json`
5. `runtime/dashboard.html`

这样可以快速判断问题是在：

- Top10 选择层
- 正文增强层
- editorial-ready 层
- 展示层
