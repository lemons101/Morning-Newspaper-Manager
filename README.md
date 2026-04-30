# Morning-Newspaper-Manager

`Morning-Newspaper-Manager` 是一个面向 OpenClaw / 晨报自动化场景的信息采集、分诊、编辑整理与静态展示项目。

它当前已经不只是一个早期信息采集原型，而是一条更完整的晨报生产链：

```text
信息来源
  -> 采集与去重
  -> triage / 候选池 / Top10
  -> 正文重抓与清洗
  -> top10_editorial_ready.json
  -> final_newspaper.json / final_newspaper.md
  -> runtime/dashboard.html
  -> 8510 固定链接展示
  -> 每日自动更新 + 每日自动推送
```

---

## 1. 当前项目定位

这个项目的目标不是“尽可能多抓数据”，而是：

- 持续收集 AI 技术、AI Agent、开源工具、商业与安全信号
- 从候选池中收敛出更值得看的 Top10
- 将 Top10 进一步整理成 **editorial-ready 素材包**
- 输出更接近成品的中文晨报页面
- 通过同一个固定链接，对外稳定展示当天晨报

当前最重要的理解是：

> 这套系统已经从“采集原型”升级成“晨报生产与展示系统”。

---

## 2. 环境与依赖前提

在接手或部署这套系统前，先明确当前默认运行前提。

### 2.1 默认目录

- 项目根目录：`/root/projects/Morning-Newspaper-Manager`
- 运行产物目录：`/root/projects/Morning-Newspaper-Manager/runtime`
- 脚本目录：`/root/projects/Morning-Newspaper-Manager/scripts`
- 文档目录：`/root/projects/Morning-Newspaper-Manager/docs`

### 2.2 Python 与运行方式

当前主流程通过本机 `python3` 运行：

```bash
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

仓库当前存在 `.venv/`，但文档层面不把它写死成唯一运行方式。实际接手时应先确认：

- `python3` 可用
- 项目依赖已安装
- `src/pipeline/collect.py` 可直接运行

建议维护者先做一次最小检查：

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 --version
python3 -c "import yaml, requests"
python3 src/pipeline/collect.py --help
```

如果这里已经失败，优先先修环境与依赖，不要直接改业务逻辑。

### 2.3 哪些内容可以进 git，哪些不要进 git

#### 可以提交到 git 的

- 项目代码
- 文档（README / docs / skill notes）
- 运行脚本
- 非敏感默认配置
- 样例结构和字段说明

#### 不建议提交到 git 的

- `.venv/`
- 本地缓存、临时文件、运行态目录垃圾
- 真实密码、token、secret、授权码
- 带账号权限的本地凭据
- 与个人环境强绑定的临时调试产物

#### 必须本地手工创建或补齐的

- Python 运行环境
- 某些依赖包
- 邮箱账号 / 授权码
- 外部搜索与消息能力所需配置
- 机器上的静态服务与定时任务运行条件

README 应当解释这些内容的**类别和用途**，但不要把真实敏感值直接写进仓库。

### 2.4 配置文件

运行前至少要确认这些配置文件存在且内容合理：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

其中：

- `app_config.yaml` 决定 runtime、triage、openclaw 等主流程行为
- `sources.yaml` 决定固定来源
- `search_topics.yaml` 决定 Tavily / 搜索主题计划

#### 这些配置文件通常需要补哪些信息

##### `config/app_config.yaml`
通常需要确认：

- runtime 输出目录
- triage 参数
- enrichment 相关开关
- openclaw / ai triage 相关开关
- dashboard 相关配置是否只是保留旧动态入口，还是仍有实际用途

字段示例（仅示意，不含敏感值）：

```yaml
app:
  timezone: Asia/Shanghai
runtime:
  output_dir: runtime
triage:
  top_n: 10
  candidate_limit: 15
openclaw:
  ai_triage_enabled: true
```

##### `config/sources.yaml`
通常需要确认：

- 启用了哪些固定来源
- 每个来源的数量上限
- 某些来源是否依赖额外配置或授权
- 邮件来源是否需要本地账号与授权码

字段示例（仅示意，不含敏感值）：

```yaml
fixed_sources:
  - id: github_high_stars
    enabled: true
    max_items: 4
  - id: executive_mailbox
    enabled: true
    user_env: IMAP_USER
    pass_env: IMAP_PASS
```

##### `config/search_topics.yaml`
通常需要确认：

- 搜索主题
- 查询词
- 域名偏好
- 每个主题的抓取上限

字段示例（仅示意，不含敏感值）：

```yaml
openclaw_tavily_search:
  enabled: true
  max_items_per_topic: 5
  topics:
    - id: ai_frontier_technology
      query: "latest AI model release multimodal reasoning inference benchmark"
```

### 2.5 需要自行准备的环境信息

这套系统当前至少可能涉及以下本地或外部信息，接手时应逐项确认：

- 邮箱账号（如启用邮件告警）
- 邮箱授权码 / IMAP / POP3 相关配置
- 某些来源的 API 访问条件（如果当前来源启用）
- OpenClaw 的消息发送能力
- Feishu 推送链路是否可用
- Tavily / web-search 协作能力是否可用
- `8510` 静态页面访问链是否正常

### 2.6 外部依赖与协作能力

这套系统并不是所有能力都在 Python 进程内部完成，当前还依赖这些外层条件：

- Tavily / web-search 结果通过文件回填，而不是 Python 里直接调用 API
- Feishu 晨报推送依赖 OpenClaw 的消息能力
- `8510` 固定链接依赖当前静态服务链保持可用
- 每日自动更新 / 推送依赖 OpenClaw cron 正常执行

### 2.7 关于旧动态 dashboard 配置的说明

当前 `config/app_config.yaml` 中仍保留了 `dashboard.host=127.0.0.1`、`dashboard.port=8502` 这类旧动态 dashboard 配置。

这不代表当前对外主入口是 8502。当前更重要的判断是：

- **动态 dashboard 配置仍然存在**
- **但当前主交付物是 `runtime/dashboard.html`**
- **当前主分享入口是 `http://101.47.152.44:8510/dashboard.html`**

接手维护时，不要因为看到 `8502` 就误以为当前主要交付链已经切回旧动态 dashboard。

### 2.8 环境初始化建议步骤

如果你是第一次在新机器上接这套系统，建议按下面顺序做：

1. 准备项目目录并确认代码完整。
2. 准备 Python 运行环境（可用系统 `python3` 或本地虚拟环境）。
3. 安装项目所需依赖。
4. 检查并补齐 `config/` 下的主配置文件。
5. 如启用邮件告警，补齐邮箱相关配置。
6. 确认 OpenClaw / Feishu / Tavily 等外层能力可用。
7. 手动跑一次 `collect.py --help` 和完整流程。
8. 确认 `runtime/dashboard.html` 已生成。
9. 再确认固定链接和自动化任务是否正常。

### 2.9 环境初始化最小验收

建议至少跑下面这组检查：

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 --version
python3 -c "import yaml, requests"
python3 src/pipeline/collect.py --help
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

最小验收标准：

- collect 命令可以正常启动
- `runtime/top10_editorial_ready.json` 已生成或更新
- `runtime/dashboard.html` 已生成或更新
- `http://101.47.152.44:8510/dashboard.html` 可以访问

### 2.10 runtime 目录的角色

`runtime/` 不是缓存垃圾桶，而是当前系统的重要运行中间层与交付层。

里面同时包含：

- 原始采集结果
- triage / Top10 中间结果
- editorial-ready 中间结果
- 最终晨报成稿
- 最终静态 HTML 页面

排查问题时，不要只盯页面，优先顺着 runtime 链往前看。

### 2.11 缺失项与补齐方式

如果接手时发现“仓库里没有某样东西”，不要先慌，也不要先乱改代码。先按下面这张思路表判断该怎么补。

#### A. 缺项目源码

补齐方式：

- 从 git 仓库 clone
- 或在已有目录里 `git pull`

适用对象：

- 项目目录不存在
- 文档、脚本、源码文件缺失

#### B. 缺 Python 环境或依赖

补齐方式：

- 创建本地 Python 环境（系统 `python3` 或虚拟环境）
- 安装依赖包
- 先跑最小验收命令确认环境通

可参考命令：

```bash
python3 --version
python3 -c "import yaml, requests"
python3 src/pipeline/collect.py --help
```

适用对象：

- `python3` 不可用
- import 失败
- collect 命令无法启动

#### C. 缺配置文件或配置值

补齐方式：

- 检查并补齐：
  - `config/app_config.yaml`
  - `config/sources.yaml`
  - `config/search_topics.yaml`
- 根据当前部署目标补充来源、开关、主题与数量上限

适用对象：

- 配置文件不存在
- 配置文件字段缺失
- 配置值不符合当前部署环境

#### D. 缺敏感信息或账号授权

补齐方式：

- 本地手工补环境变量
- 手工填写账号、授权码或凭据引用
- 不要把真实敏感值提交回 git

适用对象：

- 邮箱账号/授权码缺失
- 某些来源依赖的授权条件缺失
- OpenClaw / 消息链路权限未就绪

#### E. 缺 runtime 产物

补齐方式：

- 重新跑完整流程：

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

- 或跑每日脚本：

```bash
cd /root/projects/Morning-Newspaper-Manager
./scripts/run_daily_newspaper.sh
```

适用对象：

- `top10_editorial_ready.json` 不存在
- `final_newspaper.*` 不存在
- `dashboard.html` 不存在
- 页面内容明显过旧，需要重新生成

#### F. 缺外层系统能力

补齐方式：

- 检查 OpenClaw cron 是否存在并正常执行
- 检查 Feishu 推送链路是否可用
- 检查 Tavily / web-search 协作能力是否可用
- 检查 8510 静态服务是否可访问

适用对象：

- 页面能生成但不会自动更新
- 页面更新了但不会自动推送
- 搜索计划生成了但没有结果回填
- 固定链接不可访问

---

## 3. 快速上手（最小路径）

如果你的目标只是：**先把今天晨报跑出来，并确认页面可看**，按这条最小路径走。

### Step 1：确认项目目录与配置

确认以下路径存在：

- `/root/projects/Morning-Newspaper-Manager`
- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### Step 2：跑完整晨报链

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

### Step 3：检查关键产物是否生成

至少检查：

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/dashboard.html`

### Step 4：打开最终页面

- 本地文件：`runtime/dashboard.html`
- 固定链接：`http://101.47.152.44:8510/dashboard.html`

### Step 5：确认自动化状态

如果系统应处于自动运行状态，再继续确认：

- 每日 08:00 自动更新是否正常
- 每日 08:05 自动推送是否正常

如果只是想快速验证项目是否可用，这 5 步已经够了。

---

## 4. 当前推荐工作流

### 三层结构

#### A. 采集 / 分诊层
负责把多来源信息统一采回并初步收敛：

- 固定来源采集
- Tavily 搜索计划 / 搜索结果回填
- 邮件告警抽取
- link preview
- 去重
- triage（Urgent / Important / FYI）
- 候选池与 Top10

#### B. 编辑中间层
负责把 Top10 从“可排序条目”变成“可成稿素材”：

- 正文重抓
- 正文清洗
- `top10_enriched_items.json`
- `top10_editorial_ready.json`
- `card_title`
- `card_summary`

#### C. 展示 / 交付层
负责把中间素材变成用户真正可看的晨报：

- `final_newspaper.json`
- `final_newspaper.md`
- `runtime/dashboard.html`
- 8510 静态服务
- 每日自动更新
- 每日推送“3 条今日看点 + 链接”

---

## 5. 按 part 理解整条链路

如果你不是只想“跑一下”，而是准备接手维护，建议按下面 6 个 part 理解。

### Part A：采集层

负责：

- 固定来源采集
- Tavily 搜索计划生成与结果并入
- 邮件告警抽取

这一层的目标不是“越多越好”，而是提供足够稳定、可追踪、能进入后续 Top10 的来源底盘。

### Part B：分诊 / Top10 层

负责：

- 去重
- triage
- 候选池选择
- `top10_items.json`

这一层把原始条目收敛成更值得继续看的候选，但它还不是最终晨报成品。

### Part C：正文增强层

负责：

- link preview
- 正文抓取
- 文本清洗
- `top10_enriched_items.json`

这一层决定后面页面里的“主要内容”是否有足够信息密度。

### Part D：editorial-ready 层

负责：

- `top10_editorial_ready.json`
- `card_title`
- `card_summary`
- 编辑视角提示信息

这是当前最关键的中间层，也是页面成品感最核心的来源。

### Part E：展示层

负责：

- `final_newspaper.json`
- `final_newspaper.md`
- `runtime/dashboard.html`
- 8510 固定链接

这一层把中间素材真正变成用户可以直接打开、直接看的晨报页面。

### Part F：自动化层

负责：

- 每日 08:00 自动更新页面
- 每日 08:05 自动推送看点 + 链接

这一层保证系统从“手动生成页面”升级成“固定链接的每日晨报入口”。

---

## 6. 端到端任务流

当前真实任务流如下：

1. 读取配置：
   - `config/app_config.yaml`
   - `config/sources.yaml`
   - `config/search_topics.yaml`
2. 采集固定来源（GitHub、HN、RSS、邮件等）
3. 生成 Tavily 搜索计划并读取回填结果
4. 合并原始条目
5. enrich link previews
6. 去重
7. triage（Urgent / Important / FYI）
8. 选出 `triage_candidates`
9. 生成 `top10_items.json`
10. 对 Top10 做正文重抓与内容清洗
11. 生成 `top10_enriched_items.json`
12. 生成 `top10_editorial_ready.json`
13. 生成：
    - `final_newspaper.json`
    - `final_newspaper.md`
    - `runtime/dashboard.html`
14. 通过固定链接展示：
    - `http://101.47.152.44:8510/dashboard.html`
15. 每天 08:00 自动更新页面
16. 每天 08:05 自动推送“今日看点 + 链接”

---

## 7. 每个 part 的注意事项

这部分是 README 里最值得维护者反复看的内容。

### Part A：采集层注意事项

- 不要盲目加来源，先保证正文质量和可读性。
- Tavily 结果是**文件回填**，不是 Python 进程里直接搜。
- 邮件告警和普通资讯不要混成同一套展示逻辑。
- 来源多不等于晨报更好，弱来源会直接拉低 Top10 和页面质量。

### Part B：分诊 / Top10 层注意事项

- `top10_items.json` 只是 Top10 选择结果，不是最终成品。
- 不要把这一层的短摘要直接当页面主要内容。
- 如果 Top10 质量差，优先回看候选池和来源，而不是先怪页面样式。

### Part C：正文增强层注意事项

- 这一层决定后面“主要内容”能不能写得像样。
- 如果正文抓取失败，页面层几乎不可能靠美化补救回来。
- GitHub README、安全公告、普通文章不能完全按同一种方式处理。

### Part D：editorial-ready 层注意事项

- `top10_editorial_ready.json` 是当前最关键的中间层。
- 优先改这里，不要直接在 HTML 里写死业务逻辑。
- 页面像不像成品，关键不只是 CSS，而是这层内容是否够好。
- 不要重新退回旧 `summary_zh` 主导逻辑。

### Part E：展示层注意事项

- 静态 HTML 是当前主交付物。
- 给用户看效果时，优先给 `dashboard.html` 和固定链接。
- 如果页面结构对了但内容像老版本，多半是字段回退了。
- 当前是“固定链接 + 按天覆盖更新”，不是历史归档系统。

### Part F：自动化层注意事项

- 页面自动更新和晨报自动推送是两层逻辑，不要混为一谈。
- 如果明天看到的还是昨天内容，优先查 08:00 自动更新链。
- 如果页面更新了但没收到消息，再查 08:05 推送链。
- 这层依赖 OpenClaw cron 与消息能力，迁移环境时要一起检查。

---

## 8. 当前可交付产物

### 核心 runtime 文件

- `runtime/collected_items.json`
- `runtime/normalized_items.json`
- `runtime/triage_items.json`
- `runtime/triage_candidates.json`
- `runtime/triage_candidates_enriched.json`
- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/ai_selected_top10.json`
- `runtime/final_newspaper.json`
- `runtime/final_newspaper.md`
- `runtime/dashboard.html`
- `runtime/mail_alerts.json`
- `runtime/source_report.json`
- `runtime/search_report.json`
- `runtime/tavily_search_plan.json`

### 当前最关键的 4 个文件

如果只看最关键的几个，优先看：

1. `runtime/top10_items.json` —— Top10 候选结果
2. `runtime/top10_enriched_items.json` —— Top10 正文增强结果
3. `runtime/top10_editorial_ready.json` —— 当前最重要的编辑中间层
4. `runtime/dashboard.html` —— 当前最稳定的最终展示产物

---

## 9. 运行方式

### 9.1 跑完整晨报链路

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

这条命令会串起：

- 采集
- 去重
- triage
- Top10
- ai_triage
- newspaper_writer
- 最终 HTML 写出

### 9.2 跑每日晨报脚本

```bash
cd /root/projects/Morning-Newspaper-Manager
./scripts/run_daily_newspaper.sh
```

这个脚本用于定时任务和手动重跑。

### 9.3 只看最终页面

最终页面文件：

```text
runtime/dashboard.html
```

当前稳定访问链接：

```text
http://101.47.152.44:8510/dashboard.html
```

---

## 10. 自动化任务

### 每日 08:00
自动重跑晨报链，覆盖当天的：

- `runtime/dashboard.html`

### 每日 08:05
自动向当前 Feishu 会话推送：

- 今日晨报已更新
- 3 条今日看点
- 固定链接

当前目标体验是：

> 同一个链接，每天自动更新当天晨报；每天早上自动收到看点 + 链接提醒。

---

## 11. 当前展示入口

### 静态 HTML 是主入口

当前最推荐的展示方式不是旧动态 dashboard，而是：

- `runtime/dashboard.html`
- 8510 静态服务

原因：

- 更稳定
- 更适合手机和外部访问
- 不依赖动态会话状态
- 更适合分享固定链接

---

## 12. 当前推荐改造原则

### 原则 1：优先改 editorial-ready 中间层
如果要提升成品质量，优先围绕：

- `top10_editorial_ready.json`
- `card_title`
- `card_summary`
- `editorial_summary_hint`

而不是直接在页面上补丁式硬修。

### 原则 2：展示层优先使用新字段
当前页面应优先使用：

- `card_title`
- `card_summary`

避免重新回退到旧的 `summary_zh` 主导逻辑。

### 原则 3：静态 HTML 优先于动态 dashboard
当目标是“给用户看成品”或“给别人分享链接”时，优先保证：

- `dashboard.html`
- 8510 访问链

### 原则 4：先稳运行链，再做更复杂自动化
优先顺序建议：

1. runtime 产物稳定
2. editorial-ready 质量提升
3. 页面观感优化
4. 分享访问更稳
5. 最后再扩更多推送和集成

---

## 13. 关键注意事项

### 13.1 不要回退到旧 summary 展示链
如果页面重新优先吃旧摘要字段，页面会快速退回“老版本味道”。

当前应优先展示：

- `card_title`
- `card_summary`
- 中文“主要内容”

### 13.2 不要把项目内嵌 `openclaw infer model run` 当主生成路径
此前已验证这条路不稳定，出现过：

- `RAW_LEN=0`
- session file locked
- timeout / fallback

所以当前更稳的架构是：

> 采集 → editorial-ready → 静态生成

而不是项目内再深度内嵌模型成稿调用。

### 13.3 当前主链接是“按天覆盖”，不是历史归档
当前：

- 主链接固定
- 每天内容覆盖更新

目前不是按天保留历史 HTML 版本。如果要历史归档，需要单独设计。

### 13.4 8510 是当前分享链的一部分
不要轻易改端口、改入口或切回仅本地访问模式。当前固定对外入口是：

- `http://101.47.152.44:8510/dashboard.html`

---

## 14. 维护者第一天建议

如果你是第一次接手这套系统，建议按这个顺序进入：

1. 先读本 README，建立整体理解。
2. 再读 `docs/task_flow.md`，理解端到端链路。
3. 再读 `docs/operations.md`，理解运行、自动化和排查方式。
4. 检查 `runtime/` 当前有哪些真实产物。
5. 手动跑一次 `collect.py`，确认链路可再生。
6. 确认 `runtime/dashboard.html` 已更新。
7. 再决定你接下来要改的是来源、Top10、editorial-ready、页面还是自动化。

这样进入成本最低，也最不容易一上来就改错层。

---

## 15. 文档索引

- `docs/task_flow.md` —— 端到端任务流
- `docs/source_strategy.md` —— 信息源与通道策略
- `docs/operations.md` —— 运行、自动化、排查与维护说明

---

## 16. 项目结构（当前重点）

```text
Morning-Newspaper-Manager/
  config/
    app_config.yaml
    sources.yaml
    search_topics.yaml

  src/
    collectors/
    triage/
    dashboard/
      view_model.py
      static_html.py
    pipeline/
      collect.py
      ai_triage.py
      content_enrich.py
      newspaper_writer.py

  scripts/
    run_newspaper_writer.py
    run_daily_newspaper.sh

  runtime/
    top10_editorial_ready.json
    final_newspaper.json
    final_newspaper.md
    dashboard.html

  docs/
    task_flow.md
    source_strategy.md
    operations.md
```

---

## 17. 一句话总结

> `Morning-Newspaper-Manager` 当前是一套“采集 → Top10 → editorial-ready → 静态晨报页面 → 固定链接展示 → 每日自动更新/推送”的晨报系统，而不再只是早期的信息采集原型。
