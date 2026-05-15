# Morning-Newspaper-Manager

Morning-Newspaper-Manager 是一个围绕 **AI 早报生产链路** 构建的完整项目：

- 多来源采集候选信息
- 去重、triage、LLM 候选粗筛与 LLM 主编 Top10 终选
- 正文抓取与清洗
- 基于网页正文与大模型生成中文编辑摘要
- 生成 `top10_editorial_ready.json`
- 输出 `final_newspaper.json`、`final_newspaper.md` 与 `runtime/dashboard.html`
- 通过固定页面链接进行展示，并支持每日自动更新与推送

它既可以被当成一个晨报项目仓库使用，也可以被组织成一个 **供 OpenClaw 使用的完整 skill 项目**。

---

## 1. 项目定位

这个项目的核心目标不是“抓很多信息”，而是：

> **每天稳定地从多来源收集 AI 相关信号，先收敛成高质量候选池，再由大模型按主编口径终选 Top10，并基于网页正文生成中文编辑摘要，通过固定页面与自动推送稳定交付。**

从产品视角看，它包含 4 层：

1. **采集与分诊层**：采集、标准化、去重、triage、候选池、LLM 主编 Top10
2. **内容增强层**：正文抓取、正文清洗、网页正文理解
3. **编辑中间层**：生成 `summary_main` / `why_it_matters` / `key_points` / `card_summary`
4. **展示与交付层**：`final_newspaper.*`、`dashboard.html`、固定链接、自动推送

---

## 2. 当前推荐任务流

```text
信息来源
  -> 采集与标准化
  -> enrich / 去重 / triage
  -> LLM 候选粗筛
  -> 候选池正文增强与清洗
  -> 大模型基于网页正文生成中文编辑摘要
  -> LLM 主编终选 Top10
  -> top10_editorial_ready.json
  -> final_newspaper.json / final_newspaper.md
  -> runtime/dashboard.html
  -> 固定链接访问
  -> 每日自动更新 / 每日自动推送
```

### 关键设计判断

- `triage_candidates.json` 是候选池核心，默认约 15 条
- `ai_selected_top10.json` 是 LLM 主编终选结果；不可用时回退到规则排序
- `top10_editorial_ready.json` 是页面展示前的内容中间核心
- 页面“主要内容”应优先来自：
  - `summary_main`
  - `key_points`
  - `editorial_summary_hint`
  - `why_it_matters`
  - `card_title`
  - `card_summary`
- `why_it_matters` 只回答“为什么值得看”，不能抢占“主要内容”位
- 页面层只负责展示，不负责内容救火
- `Top10` 页面默认展示完整 **10 条**
- 固定页面访问方式是产品能力的一部分，而不是调试便利

---

## 3. 主要功能

### 3.1 多来源采集
当前支持或预留接入的来源包括：

- GitHub 高星项目
- Hacker News 热门内容
- GitHub 安全公告
- RSS 来源
- 邮件告警
- Tavily / Web Search 搜索主题结果

### 3.2 候选池与 Top10
采集结果会继续经过：

- 标准化
- enrich / link preview
- 去重
- triage
- LLM 候选粗筛，生成 `triage_candidates.json`
- 候选池正文富化，生成 `triage_candidates_enriched.json`
- LLM 生成中文 `summary_main` / `why_it_matters` / `key_points`
- LLM 主编终选 Top10，生成 `ai_selected_top10.json`

最终 Top10 不是机械按分数排序。规则层负责召回、去重、优先级和兜底；大模型负责在候选池里按 AI 主线、新闻价值、可信度、版面多样性和中文摘要质量做最终取舍。如果大模型不可用或输出格式异常，系统自动回退到规则排序。

### 3.3 editorial-ready 中间层
LLM 选出的 Top10 不直接上页面，而是先生成更可编辑的中间层：

- 正文重抓
- 文本清洗
- 基于网页正文的大模型总结
- `summary_main` / `why_it_matters` / `key_points`
- 卡片标题提炼
- 卡片主要内容提炼
- `top10_editorial_ready.json`

当前这层的验收标准已经进一步明确为：

- `summary_main` 必须优先写“这条讲了什么”
- `why_it_matters` 只补“为什么值得看”
- `主要内容` 不接受英文残片、网页导航残片、系统解释口吻
- 英文来源也必须理解后改写成自然中文，允许保留 OpenAI、GitHub、MCP、CVE 等专有名词
- 即使正文不足，也应该尽量产出自然中文摘要，而不是把 fallback 写成系统说明

### 3.4 最终晨报与页面
最终产物包括：

- `runtime/final_newspaper.json`
- `runtime/final_newspaper.md`
- `runtime/dashboard.html`

**重要：** 如果这个页面已经被当成正式访问入口使用，不要直接在 `runtime/` 上做排序实验、文案实验或来源替换实验。实验结果应先输出到独立的实验产物，再决定是否覆盖正式页面。

### 3.5 展示成稿重写（现已并入正式发布链）

当前项目已经把 `display_rewrite` 视为正式发布前的成稿层，而不再只是“好看版本实验”。

正式链路现在是：

- writer 先生成基础：
  - `runtime/top10_editorial_ready_base.json`
  - `runtime/final_newspaper_base.json`
- `scripts/run_display_rewrite.py` 直接把基础稿重写成正式展示稿：
  - `runtime/top10_editorial_ready.json`
  - `runtime/final_newspaper.json`
- `scripts/rebuild_dashboard.py` 重建：
  - `runtime/dashboard.html`

相关文件：
- Prompt：`references/display_rewrite_prompt.md`
- 历史实验输入（保留参考）：`runtime_experiments/display_rewrite/display_rewrite_input.json`
- 正式重写脚本：`scripts/run_display_rewrite.py`
- 正式重写模块：`src/pipeline/display_rewrite.py`

这条链的目标不是改采集，而是把已经入选的 Top10 条目统一重写成页面展示稿，并直接成为正式页面输出。
### 3.5 自动更新与自动推送
当前链路支持：

- 每日自动更新晨报页面
- 每日自动推送「3 条今日看点 + 页面链接」
- 通过固定页面地址稳定访问当天最新 HTML

---

## 4. 推荐目录结构

```text
Morning-Newspaper-Manager/
├── README.md
├── config/                  # 配置文件
├── docs/                    # 项目文档
├── runtime/                 # 运行产物与静态页面
├── scripts/                 # 运行入口与运维脚本
├── src/
│   ├── collectors/          # 来源采集器
│   ├── dashboard/           # 页面视图模型与 HTML 生成
│   ├── pipeline/            # 主流程
│   └── triage/              # 分诊与排序
└── requirements.txt
```

如果把它作为完整 skill 项目继续整理，建议额外补：

```text
skills/morning-newspaper-manager/
├── SKILL.md
└── references/
    ├── skill-product-architecture.md
    ├── task-flow.md
    ├── runtime-files.md
    ├── page-quality-checklist.md
    ├── troubleshooting.md
    └── interface-and-ui-options.md
```

---

## 4.1 首次 clone 跑通清单

如果你是第一次把这个项目 clone 到新环境，建议严格按下面顺序操作：

1. clone 项目到任意目录
2. 创建并激活 Python 虚拟环境
3. 安装 `requirements.txt`
4. 先选择一种运行模式：
   - Mode A：最小本地演示
   - Mode B：内容增强版晨报
   - Mode C：完整每日交付
5. 先按最小模式调整配置：
   - 关闭邮箱告警来源
   - 可先关闭 Tavily 搜索增强
6. 运行：

```bash
bash scripts/run_daily_newspaper.sh /path/to/Morning-Newspaper-Manager
```

7. 确认下面文件已经生成：
   - `runtime/top10_editorial_ready.json`
   - `runtime/final_newspaper.json`
   - `runtime/dashboard.html`
8. 打开或访问 `runtime/dashboard.html`
9. 运行 freshness / runtime chain 检查，确认链路正常
10. 跑通后，再逐步打开搜索增强、邮箱告警或消息推送

---

## 5. 环境创建

### 5.1 Python 环境
推荐在项目目录下创建虚拟环境：

```bash
cd /path/to/Morning-Newspaper-Manager
python3 -m venv .venv
source .venv/bin/activate
```

项目脚本默认会自动以“脚本所在仓库根目录”作为项目根目录；也支持两种覆盖方式：

1. 命令行传入项目根目录
2. 设置环境变量 `MORNING_NEWSPAPER_PROJECT_ROOT`

### 5.2 安装依赖

```bash
pip install -r requirements.txt
```

安装后建议先做最小验证：

```bash
python3 --version
python3 -c "import yaml, requests"
python3 src/pipeline/collect.py --help
```

如果这里失败，先修依赖，不要先改业务逻辑。

---

## 6. 配置文件

启动前至少确认这三个文件：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### 6.1 `config/app_config.yaml`
主要控制：

- runtime 输出目录
- triage 参数
- enrichment 开关
- dashboard 相关设置
- OpenClaw / AI triage 相关配置

建议：

- `triage.top_n` 通常保持 10，对应 Top10
- `triage.candidate_limit` 通常保持 15
- `dashboard.host/port` 是动态 dashboard 参数，不等于静态 HTML 对外 URL

### 6.2 `config/sources.yaml`
主要控制：

- 启用了哪些固定来源
- 每类来源抓多少条
- 邮件来源怎么接入
- 某些来源依赖哪些环境变量

建议：

- 最小模式下可先关闭 `executive_mailbox`
- 完整模式下再按需启用邮箱告警，并准备 `IMAP_USER` / `IMAP_PASS`

### 6.3 `config/search_topics.yaml`
主要控制：

- Tavily / Web Search 的主题
- 查询词
- 每个主题抓取上限

建议：

- 最小模式可先设 `openclaw_tavily_search.enabled: false`
- 增强模式可优先保留 `ai_frontier_technology` 与 `ai_agent_open_source` 等高价值主题

### 6.4 最小配置示例

下面是一套适合 Mode A 的最小配置思路：

#### `config/sources.yaml`

- 保留：
  - `github_high_stars`
  - `hackernews_top`
  - `github_security_advisories`
  - `sec_press_releases`
  - `fed_press_all`
  - `fed_press_monetary`
- 关闭：
  - `executive_mailbox`

#### `config/search_topics.yaml`

- 把：

```yaml
openclaw_tavily_search:
  enabled: false
```

先关掉，等最小链路跑通后再打开。

#### 环境变量

最小模式通常至少需要：

- `GITHUB_TOKEN`（建议提供，避免 GitHub 来源受限）

如果最小模式不启邮箱，则暂时不需要：

- `IMAP_USER`
- `IMAP_PASS`

---

## 7. 接口和界面如何选

这是给部署者的选择说明，不建议写死在 skill 主说明里。

### 7.1 搜索接口选择
可选策略：

- Tavily
- Web Search
- 仅固定来源
- 混合模式

建议：

- 想先快速跑通：优先固定来源 + 少量搜索
- 想覆盖更广：增加 Tavily 或 Web Search
- 即使搜索不可用，也应允许系统在固定来源模式下生成晨报

### 7.1.1 推荐三种运行模式

#### Mode A：最小本地演示
适合：

- 先验证项目能不能跑
- 不需要推送
- 不依赖邮箱
- 先只看 `runtime/dashboard.html`

建议：

- 保留 GitHub / Hacker News / RSS 固定来源
- 关闭 `executive_mailbox`
- 可先关闭 `openclaw_tavily_search.enabled`

#### Mode B：内容增强版晨报
适合：

- 希望晨报内容更完整
- 愿意启用搜索增强
- 仍然不强求消息推送

建议：

- 启用固定来源
- 启用 Tavily / Web Search 增强
- 保留静态 HTML 作为主交付

#### Mode C：完整每日交付
适合：

- 希望每天自动更新晨报
- 希望通过消息渠道收到提醒
- 愿意维护邮箱 / 推送 / 部署环境

建议：

- 启用固定来源
- 启用搜索增强
- 按需启用邮件告警来源
- 配置推送渠道
- 配置固定访问地址或反向代理

### 7.2 LLM 接口选择
正文总结相关模型负责生成：

- `summary_main`
- `why_it_matters`
- `key_points`

建议：

- 优先选择对长文本总结稳定、中文输出自然的模型
- 对重点条目优先保证正文总结质量
- fallback 只作为兜底，不应成为主路径

### 7.3 推送方式选择
可选策略：

- Feishu 推送
- 其他消息渠道推送
- 不推送，仅生成页面

建议：

- 静态页面 + 固定链接应始终是主交付物
- 推送更适合作为晨报提醒入口，而不是唯一交付方式

### 7.4 页面展示方式选择
可选策略：

#### 方案 1：静态 HTML（推荐）
- 最稳
- 最适合分享
- 最适合固定链接
- 最适合每日覆盖更新

#### 方案 2：动态 dashboard
- 更适合内部调试
- 适合研发或验证阶段
- 不建议作为唯一正式交付方式

#### 方案 3：仅 JSON / Markdown 输出
- 适合机器消费或二次集成
- 不适合直接作为面对人的晨报成品

---

## 7.5 页面访问地址与部署说明

当前仓库默认产出的是：

- `runtime/dashboard.html`

你可以按自己的环境选择访问方式。**不要把某个公网 IP 当成产品固定真相**；公网地址、域名、反向代理方式都应由部署环境决定。

### 本地直接查看

最简单的方式是直接打开：

- `runtime/dashboard.html`

适合：

- 开发验证
- 内容检查
- 本机预览

### 本地起静态文件服务

例如：

```bash
cd /path/to/Morning-Newspaper-Manager/runtime
python3 -m http.server 8510
```

然后访问：

- `http://127.0.0.1:8510/dashboard.html`

适合：

- 本机浏览器查看
- 局域网内测试

### 服务器 / VPS 对外访问

如果你在服务器上部署，可以把 `runtime/` 目录通过静态服务暴露出来，例如：

- 直接监听 `0.0.0.0:8510`
- 放到 Nginx / Caddy / 反向代理后面
- 绑定自己的域名或公网 IP

此时推荐把对外地址当作“部署配置”，而不是项目常量。例如：

- `http://your-host:8510/dashboard.html`
- `https://your-domain/dashboard.html`

### 推荐原则

- 项目内部只保证生成 `runtime/dashboard.html`
- 访问地址由部署方式决定
- README 中的 URL 只作为示例，不应写死为唯一真相

### 7.6 本轮页面与摘要修复后的关键规则

这部分是这轮真实排查后沉淀下来的约束，后续继续改页面或摘要时，建议直接遵守：

#### A. Top10 展示层不要再吞条目
- `Top10` 默认就应展示完整 **10 条**
- 不要在 `view_model` 里因为 `body_quality == thin` 等展示层判断再过滤掉条目
- 如果出现“数据有 10 条、页面只看到 9 条”，优先检查 `src/dashboard/view_model.py`

#### B. `今日看点` 和 `Top10` 不能走两套摘要逻辑
- `lead / 今日看点` 应尽量复用与 `Top10 主卡片` 一致的中文摘要链路
- 如果 `Top10` 已修好，但 `今日看点` 还显示英文残片或旧 fallback，优先检查 `src/dashboard/view_model.py` 的 `_build_lead_bullets(...)`

#### C. 摘要字段优先级要固定
页面主摘要推荐优先级：

1. `summary_main`
2. `key_points[0]`
3. `editorial_summary_hint`
4. `why_it_matters`
5. 其他兜底

不要过早回退到 `why_it_matters`，否则页面会重新变成空泛解释句。

#### D. 主摘要的页面验收标准
只要出现在页面 `主要内容` 位，就默认要满足：

- 中文
- 先讲内容
- 再讲价值
- 不能像网页碎片
- 不能像系统注释
- 不能是“更适合作为……”“值得继续观察……”这种空泛句

---

## 8. 运行方式

### 8.1 整链运行（推荐）

```bash
bash scripts/run_daily_newspaper.sh
```

如果项目不在当前默认目录，可显式传入项目根目录：

```bash
bash scripts/run_daily_newspaper.sh /path/to/Morning-Newspaper-Manager
```

适用于：

- 重新跑当天晨报
- 定时任务
- 一键更新页面

### 8.2 仅重跑内容层

```bash
python3 scripts/run_newspaper_writer.py
```

也支持显式传入项目根目录：

```bash
python3 scripts/run_newspaper_writer.py /path/to/Morning-Newspaper-Manager
```

适用于：

- Top10 已有
- 只想重做 editorial-ready / final_newspaper / 页面内容

### 8.3 仅重建页面层

```bash
python3 scripts/rebuild_dashboard.py
```

也支持显式传入项目根目录：

```bash
python3 scripts/rebuild_dashboard.py /path/to/Morning-Newspaper-Manager
```

适用于：

- 内容已准备好
- 只想重建 `runtime/dashboard.html`

### 8.4 健康检查与 freshness 检查

```bash
python3 scripts/check_runtime_chain.py
python3 scripts/check_runtime_chain.py /path/to/Morning-Newspaper-Manager
bash scripts/check_dashboard_freshness.sh /path/to/project http://your-host:8510/dashboard.html
```

适用于：

- 检查 runtime 主链产物是否齐全
- 检查本地页面与远端页面是否为最新版本

---

## 9. 当前最重要的运行产物

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/final_newspaper.json`
- `runtime/dashboard.html`

这几个文件分别对应：

- Top10 是否选对
- 正文是否抓到
- 编辑中间层是否成型
- 成稿是否正常
- 页面最终是否对外可看

---

## 10. 页面质量验收标准

如果你要判断“这版页面算不算已经能发给别人看”，建议至少检查：

1. Top10 是否完整展示 10 条
2. `top10_editorial_ready.json` 是否不是空文件
3. 头部主要条目的 `summary_main` / `why_it_matters` / `key_points` 是否已有中文编辑摘要
4. 页面里的主要内容是否以中文为主
5. 是否出现网页导航噪音、metadata dump、英文脏摘要
6. 页面是否已经输出到 `runtime/dashboard.html`
7. 固定访问方式是否可用，且页面时间戳是最新的

---

## 11. 推荐排查顺序

如果页面内容不对，建议按顺序排查：

1. `runtime/top10_items.json`
2. `runtime/top10_enriched_items.json`
3. `runtime/top10_editorial_ready.json`
4. `runtime/final_newspaper.json`
5. `runtime/dashboard.html`

这样可以快速判断问题是在：

- Top10 选择层
- 正文增强层
- editorial-ready 层
- 成稿层
- 展示层

如果页面访问不对，再查：

- 服务是否监听正确端口
- 页面文件时间戳与 `Last-Modified`
- 缓存 / 映射 / 对外可达性
- 你当前使用的是本地文件、本地静态服务，还是反向代理后的外部 URL

---

## 12. 作为 OpenClaw skill 项目继续整理的建议

如果你的目标是：

> 让别人 clone 下来，并让 OpenClaw 使用这个 skill 后，也能跑出类似晨报效果

推荐继续按下面顺序推进：

1. 统一 README / SKILL / task flow / references 的叙事
2. 规范整链、内容层、页面层的入口脚本
3. 真正产品化 `summary_main` / `why_it_matters` / `key_points` 的正文 + LLM 生成链路
4. 参数化路径、URL、接口与推送方式
5. 减少本机硬编码和人工 patch 依赖

---

## 13. 页面 freshness 检查

你可以这样检查本地文件与远端地址是否一致：

```bash
bash scripts/check_dashboard_freshness.sh /path/to/Morning-Newspaper-Manager http://your-host:8510/dashboard.html
```

如果只想检查本地文件，也可以只传项目根目录：

```bash
bash scripts/check_dashboard_freshness.sh /path/to/Morning-Newspaper-Manager
```

---

## 14. 推荐验证命令

### 运行整链

```bash
bash scripts/run_daily_newspaper.sh /path/to/Morning-Newspaper-Manager
```

### 检查 runtime 主链

```bash
python3 scripts/check_runtime_chain.py /path/to/Morning-Newspaper-Manager
```

### 重建页面

```bash
python3 scripts/rebuild_dashboard.py /path/to/Morning-Newspaper-Manager
```

### freshness 检查

```bash
bash scripts/check_dashboard_freshness.sh /path/to/Morning-Newspaper-Manager http://your-host:8510/dashboard.html
```

---

## 15. 相关文档

建议优先阅读：

- `docs/task_flow.md`
- `docs/operations.md`
- `docs/source_strategy.md`

如果以 OpenClaw skill 项目视角继续整理，还应结合：

- `skills/morning-newspaper-manager/SKILL.md`
- `skills/morning-newspaper-manager/references/skill-product-architecture.md`
- `skills/morning-newspaper-manager/references/task-flow.md`
- `skills/morning-newspaper-manager/references/runtime-files.md`
- `skills/morning-newspaper-manager/references/page-quality-checklist.md`
- `skills/morning-newspaper-manager/references/troubleshooting.md`
- `skills/morning-newspaper-manager/references/interface-and-ui-options.md`
- `skills/morning-newspaper-manager/references/config-selection.md`
- `skills/morning-newspaper-manager/references/deployment-options.md`
