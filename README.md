# Morning-Newspaper-Manager

Morning-Newspaper-Manager 是一个面向 **AI / Agent / 开源工具 / 商业与安全信号** 的晨报生产项目。

它不是单纯的信息抓取脚本，而是一条完整的晨报生成链路：

- 采集多源信息
- 去重、分诊、排序
- 收敛 Top10
- 对 Top10 做正文增强与清洗
- 生成可编辑的 editorial-ready 素材
- 输出最终中文晨报与静态页面
- 通过固定链接对外展示
- 支持每日自动更新与自动推送

---

## 1. 核心功能

### 1.1 多源信息采集
支持从多类来源收集候选信息，包括：

- GitHub 高星项目
- Hacker News 热门内容
- GitHub 安全公告
- RSS 资讯源
- 邮箱告警
- Tavily / Web Search 主题搜索结果

### 1.2 候选池与 Top10 收敛
项目会对采集结果做统一处理：

- 结构标准化
- link preview enrich
- 去重
- triage（Urgent / Important / FYI）
- 候选池排序
- 输出 Top10

### 1.3 正文增强与 editorial-ready 生成
针对 Top10 条目继续处理：

- 正文重抓
- 文本清洗
- 提炼卡片标题
- 提炼卡片主要内容
- 生成 `top10_editorial_ready.json`

这一层的目标是把“可排序条目”升级成“可成稿素材”。

### 1.4 最终晨报与静态页面输出
项目最终输出：

- `final_newspaper.json`
- `final_newspaper.md`
- `runtime/dashboard.html`

当前页面主入口是静态 HTML，而不是旧的动态 dashboard。

### 1.5 自动化更新与自动推送
当前链路支持：

- 每日自动更新晨报页面
- 每日自动推送「3 条今日看点 + 页面链接」

---

## 2. 项目流程概览

完整链路可以理解为：

```text
信息来源
  -> 采集与标准化
  -> enrich / 去重 / triage
  -> 候选池 / Top10
  -> 正文增强与清洗
  -> top10_editorial_ready.json
  -> final_newspaper.json / final_newspaper.md
  -> runtime/dashboard.html
  -> 固定链接展示
  -> 每日自动更新 / 每日自动推送
```

当前最关键的中间产物是：

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/dashboard.html`

---

## 3. 目录结构

```text
Morning-Newspaper-Manager/
├── config/                  # 配置文件
├── docs/                    # 补充文档
├── runtime/                 # 运行产物与最终页面
├── scripts/                 # 运行脚本
├── src/                     # 主代码
│   ├── collectors/          # 来源采集器
│   ├── dashboard/           # 页面视图模型与静态 HTML 生成
│   ├── pipeline/            # 主流程串联
│   └── triage/              # 分诊与排序逻辑
└── README.md
```

---

## 4. 环境要求

### 4.1 基础运行环境
建议至少具备：

- Linux / macOS 环境
- `python3`
- 可访问外网的运行环境（部分来源抓取依赖外网）

### 4.2 Python 依赖
当前主流程通过 `python3` 直接运行：

```bash
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

建议先验证：

```bash
python3 --version
python3 -c "import yaml, requests"
```

如果这里已经失败，优先修 Python 环境和依赖。

### 4.3 本地环境与 Git 边界
以下内容**不建议提交到 Git**：

- `.venv/`
- 本地缓存 / 临时文件
- 真实密码 / token / secret / 授权码
- 与个人环境强绑定的本地凭据

以下内容通常**应该随仓库提交**：

- 项目代码
- 文档
- 运行脚本
- 非敏感默认配置
- 配置结构说明

---

## 5. 配置说明

项目启动前至少要确认以下配置文件：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### 5.1 `config/app_config.yaml`
主要控制：

- runtime 输出目录
- triage 参数
- enrichment 开关
- OpenClaw / AI triage 开关
- dashboard 相关设置

示例：

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

### 5.2 `config/sources.yaml`
主要控制：

- 启用哪些固定来源
- 每类来源抓多少条
- 某些来源使用哪些环境变量或授权条件
- 邮箱告警的采集参数

示例：

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

### 5.3 `config/search_topics.yaml`
主要控制：

- Tavily / Web Search 搜索主题
- 查询词
- 域名偏好
- 每个主题的结果上限

示例：

```yaml
openclaw_tavily_search:
  enabled: true
  max_items_per_topic: 5
  topics:
    - id: ai_frontier_technology
      query: "latest AI model release multimodal reasoning inference benchmark"
```

---

## 6. 需要自行补齐的环境信息

以下内容通常不会直接写进仓库，需要在目标环境里自行补齐：

- 邮箱账号
- 邮箱授权码 / IMAP / POP3 参数
- 某些来源所需 API 凭据
- OpenClaw 消息发送能力
- Feishu 推送链路能力
- Tavily / Web Search 协作能力
- 静态页面服务能力

如果缺失这些内容，项目不一定完全不能跑，但某些来源、自动推送或固定链接展示会失效。

---

## 7. 快速开始

### 7.1 获取项目

```bash
git clone <your-repo-url>
cd Morning-Newspaper-Manager
```

### 7.2 检查配置
确认以下文件存在并已按你的环境补齐：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### 7.3 跑完整晨报链路

```bash
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

### 7.4 检查关键产物
至少检查：

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/dashboard.html`

### 7.5 打开页面

- 本地文件：`runtime/dashboard.html`
- 当前固定链接：`http://101.47.152.44:8510/dashboard.html`

---

## 8. 常用运行方式

### 8.1 完整主流程入口

```bash
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

这是当前最重要的主入口，会串起：

- 采集
- enrich
- 去重
- triage
- Top10
- 内容增强
- 晨报生成
- 静态页面输出

### 8.2 每日运行脚本

```bash
./scripts/run_daily_newspaper.sh
```

适合：

- 定时任务
- 手动重跑
- 每日晨报更新

### 8.3 关于 `scripts/run_newspaper_writer.py`
这个脚本不是每日自动更新的必要入口。

它的作用更偏向：

- 单独重跑最终成稿 / 页面生成步骤
- 开发或排查时只重建最后一段产物

即使没有它，只要完整主流程入口还在，晨报页面依然可以正常生成和更新。

---

## 9. 自动化说明

当前自动化链路分为两层：

### 9.1 页面自动更新
负责：

- 每日自动重跑主流程
- 更新当天 `runtime/dashboard.html`
- 覆盖固定链接看到的晨报页面

### 9.2 晨报自动推送
负责：

- 在晨报生成后提取今日看点
- 向目标用户推送「3 条今日看点 + 页面链接」

也就是说：

- 自动更新页面
- 自动发送晨报

是两层逻辑，不要混为一谈。

---

## 10. 输出产物说明

### 10.1 关键 runtime 文件

- `runtime/collected_items.json`
- `runtime/normalized_items.json`
- `runtime/triage_items.json`
- `runtime/triage_candidates.json`
- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/final_newspaper.json`
- `runtime/final_newspaper.md`
- `runtime/dashboard.html`

### 10.2 最值得优先看的文件
如果只看几个关键文件，建议优先看：

1. `runtime/top10_items.json`
2. `runtime/top10_enriched_items.json`
3. `runtime/top10_editorial_ready.json`
4. `runtime/dashboard.html`

---

## 11. 故障排查

### 11.1 页面没更新
优先检查：

- 主流程是否真的执行
- `runtime/dashboard.html` 是否重新生成
- 08:00 自动更新任务是否正常

### 11.2 页面更新了，但没收到推送
优先检查：

- 08:05 推送任务是否正常
- OpenClaw / Feishu 消息链路是否可用

### 11.3 页面内容像旧版本
优先检查：

- `top10_editorial_ready.json` 是否更新
- 页面是否回退读取旧摘要字段
- 主流程是否真正走到正文增强和 editorial-ready 阶段

### 11.4 搜索没有结果
优先检查：

- `config/search_topics.yaml` 是否启用
- Tavily / Web Search 结果是否有回填
- 外部协作链路是否正常

### 11.5 邮箱来源异常
优先检查：

- 邮箱账号与授权码是否正确
- IMAP / POP3 参数是否正确
- 邮件过滤规则是否过严

---

## 12. 设计原则

当前项目的核心原则是：

1. **优先保证晨报成品质量，而不是单纯抓更多数据**
2. **优先改中间层内容质量，而不是只改页面样式**
3. **静态 HTML 是当前主交付物**
4. **自动更新链与自动推送链要分开看**
5. **不要把本地环境、敏感值、临时产物直接提交到 Git**

---

## 13. 补充文档

更多细节可参考：

- `docs/task_flow.md`
- `docs/source_strategy.md`
- `docs/operations.md`

---

## 14. 一句话总结

Morning-Newspaper-Manager 是一个把 **信息采集 → Top10 收敛 → 正文增强 → 中文晨报成稿 → 静态页面展示 → 自动推送** 串起来的晨报生产项目。
