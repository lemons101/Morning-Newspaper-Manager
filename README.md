# Morning-Newspaper-Manager

Morning-Newspaper-Manager 是一个把 **信息采集 → 分诊排序 → Top10 收敛 → 正文增强 → 中文晨报成稿 → 静态页面展示 → 自动推送** 串起来的晨报生产项目。

它关注的不是“抓得越多越好”，而是：

- 从多类来源收集候选信息
- 收敛出更值得看的 Top10
- 生成更像成品的中文晨报
- 用固定链接稳定展示当天晨报
- 支持每天自动更新与自动推送

---

## 1. 主要功能

### 1.1 多源采集
当前支持或预留接入的来源包括：

- GitHub 高星项目
- Hacker News 热门内容
- GitHub 安全公告
- RSS 来源
- 邮箱告警
- Tavily / Web Search 搜索主题结果

### 1.2 候选池与 Top10
采集结果会继续经过：

- 标准化
- enrich / link preview
- 去重
- triage
- 候选池排序
- Top10 输出

### 1.3 editorial-ready 中间层
Top10 不直接上页面，而是先生成更可编辑的中间层：

- 正文重抓
- 文本清洗
- 卡片标题提炼
- 卡片主要内容提炼
- `top10_editorial_ready.json`

### 1.4 最终晨报与页面
最终产物包括：

- `runtime/final_newspaper.json`
- `runtime/final_newspaper.md`
- `runtime/dashboard.html`

### 1.5 自动更新与自动推送
当前链路支持：

- 每日自动更新晨报页面
- 每日自动推送「3 条今日看点 + 页面链接」

---

## 2. 项目流程

```text
信息来源
  -> 采集与标准化
  -> enrich / 去重 / triage
  -> 候选池 / Top10
  -> 正文增强与清洗
  -> top10_editorial_ready.json
  -> final_newspaper.json / final_newspaper.md
  -> runtime/dashboard.html
  -> 8510 固定链接展示
  -> 每日自动更新 / 每日自动推送
```

当前最重要的几个运行产物是：

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
├── runtime/                 # 运行产物与静态页面
├── scripts/                 # 运行脚本
├── src/
│   ├── collectors/          # 来源采集器
│   ├── dashboard/           # 页面视图模型与 HTML 生成
│   ├── pipeline/            # 主流程
│   └── triage/              # 分诊与排序
└── README.md
```

---

## 4. 环境创建

这部分不要只看“原则”，按步骤做。

### 4.1 Python 环境
推荐直接在项目目录下创建虚拟环境：

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 -m venv .venv
source .venv/bin/activate
```

如果你不想用虚拟环境，也至少保证系统 `python3` 可用。

### 4.2 安装依赖
当前仓库已经补了一个基础 `requirements.txt`，先按它安装：

```bash
pip install -r requirements.txt
```

当前这个文件优先覆盖项目主链和旧动态 dashboard 入口所需的基础依赖，包括：

- `PyYAML`
- `requests`
- `streamlit`

安装后先做最小验证：

```bash
python3 --version
python3 -c "import yaml, requests, streamlit"
```

如果这里失败，先修依赖，不要先改业务逻辑。

### 4.3 最小可运行验证
建议先跑下面三步：

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 --version
python3 -c "import yaml, requests"
python3 src/pipeline/collect.py --help
```

如果 `collect.py --help` 都起不来，说明环境还没准备好。

### 4.4 不要提交到 Git 的内容
以下内容不要传到仓库：

- `.venv/`
- 本地缓存 / 临时文件
- 真实密码 / token / secret / 授权码
- 与个人环境强绑定的本地凭据

---

## 5. 配置文件

项目启动前，至少要确认这三个文件：

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
  skill_run_command: openclaw skills run
  ai_triage_enabled: true
```

### 5.2 `config/sources.yaml`
主要控制：

- 启用了哪些固定来源
- 每类来源抓多少条
- 邮件来源怎么接入
- 某些来源依赖哪些环境变量

示例：

```yaml
- id: github_high_stars
  type: github_high_stars
  enabled: true
  max_items: 4
  auth_env: GITHUB_TOKEN

- id: executive_mailbox
  type: mail_alerts
  enabled: true
  host: imap.163.com
  port: 993
  pop_host: pop.163.com
  pop_port: 995
  user_env: IMAP_USER
  pass_env: IMAP_PASS
  folders:
    - INBOX
```

### 5.3 `config/search_topics.yaml`
主要控制：

- Tavily / Web Search 的主题
- 查询词
- 每个主题抓取上限

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

## 6. 邮件配置怎么填

这部分是实操重点。

### 6.1 你需要准备什么
如果启用邮箱告警来源，至少需要：

- 邮箱账号
- 邮箱授权码（不是登录密码时，以服务商的 IMAP/POP 授权码为准）
- IMAP host / port
- POP host / port（如果启用了 POP fallback）

### 6.2 配置文件里填哪里
邮件源主要写在：

- `config/sources.yaml`

一个更完整的示例块可以长这样：

```yaml
- id: executive_mailbox
  type: mail_alerts
  enabled: true
  name: 重要邮箱告警
  max_items: 5
  host: imap.163.com
  port: 993
  pop_host: pop.163.com
  pop_port: 995
  pop3_fallback_enabled: true
  user_env: IMAP_USER
  pass_env: IMAP_PASS
  folders:
    - INBOX
  max_messages: 50
  lookback_hours: 72
  initial_backfill_hours: 336
```

### 6.3 账号和授权码怎么注入
不要把真实邮箱账号和授权码直接写进仓库。

建议在当前 shell 里注入：

```bash
export IMAP_USER="your_mail@example.com"
export IMAP_PASS="your_authorization_code"
```

如果还需要 GitHub API：

```bash
export GITHUB_TOKEN="your_github_token"
```

### 6.4 怎么验证邮箱配置有没有生效
最简单的办法不是先看页面，而是：

1. 确认环境变量已经 export
2. 确认 `config/sources.yaml` 邮件源是 `enabled: true`
3. 跑一次主流程
4. 查看 runtime 里有没有新的邮件来源结果进入候选池

如果邮件源没有任何结果，优先检查：

- 邮箱账号是否正确
- 授权码是否正确
- IMAP / POP 参数是否正确
- 服务商是否开启了 IMAP / POP 权限

---

## 7. Tavily / Web Search skill 怎么安装

### 7.1 先确认 OpenClaw 可用

```bash
openclaw --version
openclaw skills --help
```

### 7.2 如果需要通过 ClawHub 安装 skill
OpenClaw 当前可以通过 ClawHub CLI 管理 skill。

先安装 ClawHub：

```bash
npm i -g clawhub
```

常用命令：

```bash
clawhub search tavily
clawhub search web-search
clawhub install <skill-name>
clawhub list
```

也可以更新：

```bash
clawhub update <skill-name>
```

### 7.3 安装完成后怎么验证
你至少要确认两件事：

1. skill 已经安装在 OpenClaw 可见的 skills 目录
2. OpenClaw 能识别到它

可以先看：

```bash
openclaw skills list
```

如果项目里某个配置启用了 Tavily / Web Search，但 OpenClaw 看不到对应 skill，那么搜索协作链就不会正常工作。

### 7.4 README 这里的边界
这里的目标不是把所有 skill 内部逻辑解释一遍，而是让维护者知道：

- skill 没装怎么办
- 用什么命令装
- 装完怎么验

---

## 8. 静态页面服务怎么开

这个部分非常关键，因为“页面生成了”和“别人能访问到”是两回事。

### 8.1 页面文件在哪里
最终页面文件在：

```text
runtime/dashboard.html
```

### 8.2 当前服务方式是什么
这台机器上当前就是用一个简单的 Python 静态服务脚本把 `runtime/` 目录暴露出来：

- 文件：`runtime/static_dashboard_server.py`
- 监听：`0.0.0.0:8510`

当前脚本内容本质上就是：

```python
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os

root = Path('/root/projects/Morning-Newspaper-Manager/runtime')
os.chdir(root)
server = ThreadingHTTPServer(('0.0.0.0', 8510), SimpleHTTPRequestHandler)
server.serve_forever()
```

### 8.3 怎么手动启动静态服务

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 runtime/static_dashboard_server.py
```

### 8.4 怎么确认服务已经起来
先看监听：

```bash
ss -ltnp | grep 8510
```

如果成功，你应该能看到类似：

```text
0.0.0.0:8510
```

### 8.5 本机怎么验证

```bash
curl http://127.0.0.1:8510/dashboard.html
```

### 8.6 外部访问为什么会失败
常见原因只有几类：

- 服务只监听了 `127.0.0.1`，没有监听 `0.0.0.0`
- 机器防火墙没放行 `8510`
- 云主机安全组没放行 `8510`
- 页面文件还没生成

### 8.7 开端口要检查什么
如果你要让手机、外网或其他设备访问，通常要确认：

1. 服务监听地址是 `0.0.0.0`
2. 机器本地防火墙放行了 `8510`
3. 云厂商安全组 / 防火墙规则放行了 `8510`
4. 实际访问用的是机器可达 IP，而不是 `127.0.0.1`

### 8.8 当前固定链接
当前对外固定链接是：

```text
http://101.47.152.44:8510/dashboard.html
```

---

## 9. 快速开始

### 9.1 获取项目

```bash
git clone <your-repo-url>
cd Morning-Newspaper-Manager
```

### 9.2 创建环境并安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 9.3 准备环境变量

```bash
export IMAP_USER="your_mail@example.com"
export IMAP_PASS="your_authorization_code"
export GITHUB_TOKEN="your_github_token"
```

按需补，不是每个来源都必须启用。

### 9.4 检查配置文件
确认这些文件存在并符合你的环境：

- `config/app_config.yaml`
- `config/sources.yaml`
- `config/search_topics.yaml`

### 9.5 跑完整晨报链路

```bash
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

### 9.6 检查关键产物
至少检查：

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/top10_editorial_ready.json`
- `runtime/dashboard.html`

### 9.7 启动静态页面服务

```bash
python3 runtime/static_dashboard_server.py
```

然后访问：

```text
http://127.0.0.1:8510/dashboard.html
```

如果要外部访问，再检查端口放行。

---

## 10. 常用运行方式

### 10.1 完整主流程入口

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

### 10.2 每日运行脚本

```bash
./scripts/run_daily_newspaper.sh
```

这个脚本当前很薄，本质上就是直接跑：

```bash
python3 src/pipeline/collect.py --project-root "$PROJECT_ROOT"
```

适合：

- 定时任务
- 手动重跑
- 每日晨报更新

### 10.3 `scripts/run_newspaper_writer.py` 是干嘛的
它不是每日自动更新的必要入口。

它的作用更偏向：

- 单独重跑最终成稿 / 页面生成步骤
- 开发或排查时只重建最后一段产物

即使没有它，只要完整主流程入口还在，晨报页面依然可以正常生成和更新。

---

## 11. 自动化说明

当前自动化链路分两层：

### 11.1 晨报页面自动更新
负责：

- 每日自动重跑主流程
- 更新当天 `runtime/dashboard.html`
- 覆盖固定链接看到的晨报页面

### 11.2 晨报自动推送
负责：

- 在晨报生成后提取今日看点
- 向目标用户推送「3 条今日看点 + 页面链接」

所以：

- 页面自动更新
- 晨报自动发送

是两层逻辑，不要混为一谈。

---

## 12. 输出产物

### 12.1 关键 runtime 文件

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

### 12.2 最值得优先看的文件
如果只看几个关键文件，建议优先看：

1. `runtime/top10_items.json`
2. `runtime/top10_enriched_items.json`
3. `runtime/top10_editorial_ready.json`
4. `runtime/dashboard.html`

---

## 13. 故障排查

### 13.1 页面没更新
优先检查：

- 主流程是否真的执行
- `runtime/dashboard.html` 是否重新生成
- 自动更新任务是否正常

### 13.2 页面更新了，但没收到推送
优先检查：

- 自动推送任务是否正常
- OpenClaw / Feishu 消息链路是否可用

### 13.3 外部打不开页面
优先检查：

- `8510` 是否在监听
- 是否监听在 `0.0.0.0`
- 防火墙 / 安全组是否放行 `8510`
- 访问地址是不是误用了 `127.0.0.1`

### 13.4 邮件来源没有结果
优先检查：

- `IMAP_USER` / `IMAP_PASS` 是否已 export
- 邮件源是否启用
- IMAP / POP 参数是否正确
- 服务商是否开启了 IMAP / POP 权限

### 13.5 搜索没有结果
优先检查：

- `config/search_topics.yaml` 是否启用
- skill 是否已安装
- OpenClaw 是否识别到对应 skill
- 外部协作链路是否正常

---

## 14. 补充文档

更多细节可参考：

- `docs/task_flow.md`
- `docs/source_strategy.md`
- `docs/operations.md`

---

## 15. 一句话总结

Morning-Newspaper-Manager 是一个把 **多源信息 → Top10 → editorial-ready → 中文晨报 → 静态页面 → 自动推送** 串起来的晨报生产项目；README 的重点不是讲概念，而是帮助维护者把环境、配置、skill、静态服务和自动化链真正跑通。
