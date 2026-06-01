# 第 14 节 实验手册：AI 定时早报与自动推送机器人

> 配套课程：AI 业务流架构师 · 第 14 节《AI 定时早报与自动推送机器人》
> 预计耗时：45–75 分钟（含云服务器端口配置）
> 操作方式：主要在当前渠道里和龙虾对话完成，云控制台端口放行需要手动操作
> 前置条件：OpenClaw 已部署 + 龙虾可正常对话 + 有服务器 / 火山云控制台权限

---

## 0. 开始前确认

| # | 物料 | 备注 |
|---|---|---|
| 1 | 龙虾可正常对话 | 在当前渠道发一句话能收到回复 |
| 2 | GitHub 仓库访问权限 | 能 clone `Morning-Newspaper-Assistant` 完整仓库 |
| 3 | 云服务器 | 默认项目目录为 `/root/projects/Morning-Newspaper-Assistant` |
| 4 | 火山云控制台权限 | 用于放行早报页面端口 `8510` |
| 5 | 固定页面链接 | `http://101.47.152.44:8510/dashboard.html` |
| 6 | 邮箱授权信息（可选） | 如需接入邮箱提醒，准备 `IMAP_USER` / `IMAP_PASS` |

> 注意：本节使用 **Morning-Newspaper-Assistant** 正式链路，不混用 `Morning-Newspaper-Manager`。

---

## 1. 部署项目（发给龙虾）

在当前渠道里发送以下消息：

```text
请从 GitHub 拉取并初始化 Morning-Newspaper-Assistant 项目，用于每天自动生成 AI 早报。

仓库地址：git@github.com:lemons101/Morning-Newspaper-Assistant.git
HTTPS 备用地址：https://github.com/lemons101/Morning-Newspaper-Assistant.git

要求：
1. 必须 clone 完整仓库，不要只复制某个 skill 子目录
2. 不要混用 Morning-Newspaper-Manager
3. 不要直接在正式发布链路上做未验证改动
4. 默认项目目录使用 /root/projects/Morning-Newspaper-Assistant

初始化步骤：
1. mkdir -p /root/projects
2. cd /root/projects
3. 如果 Morning-Newspaper-Assistant 不存在，就 clone 仓库；如果已存在，就进入目录并执行 git pull
4. cd /root/projects/Morning-Newspaper-Assistant
5. python3 -m venv .venv（如已存在跳过）
6. source .venv/bin/activate
7. pip install -r requirements.txt

完成后告诉我：
- 当前项目路径
- git clone / git pull 是否成功
- Python 虚拟环境是否可用
- requirements.txt 依赖是否安装成功
```

龙虾完成后，你应该收到部署确认。

---

## 2. 配置邮箱提醒（可选，手动 + 发给龙虾）

邮箱接入用于给早报增加“重要邮件 / 会议 / 截止事项提醒”，不是用来发送早报消息。早报最终仍然由龙虾发到当前渠道。

如果不需要邮箱提醒，可以跳过本节。

### 2.1 获取 163 邮箱授权码（手动）

在 163 邮箱网页中操作：

```text
登录 163 邮箱
-> 设置
-> POP3/SMTP/IMAP
-> 开启 IMAP/SMTP 服务
-> 如需备用，也开启 POP3/SMTP 服务
-> 生成客户端授权码
```

> `IMAP_PASS` 填的是客户端授权码，不是邮箱登录密码。

### 2.2 写入项目配置（发给龙虾）

把真实值替换进去，发送：

```text
请帮我配置 Morning-Newspaper-Assistant 的邮箱环境变量。

在 /root/projects/Morning-Newspaper-Assistant/.env 中写入：

IMAP_USER=你的163邮箱地址
IMAP_PASS=你的163邮箱授权码

完成后请确认：
1. .env 文件是否存在
2. IMAP_USER 是否已配置
3. IMAP_PASS 是否已配置，但不要把完整授权码发出来
```

如果不想接入邮箱，也可以发：

```text
本次不接入邮箱提醒。请确认 Morning-Newspaper-Assistant 在没有 IMAP_USER / IMAP_PASS 的情况下，会自动跳过邮件源。
```

---

## 3. 运行一次正式生成链路（发给龙虾）

发送：

```text
请用 Morning-Newspaper-Assistant 跑一次正式早报生成链路。

项目目录：
/root/projects/Morning-Newspaper-Assistant

要求：
1. 先严格按 Assistant skill 流程运行，产出：
   - runtime/collected_raw.json
   - runtime/content_enriched.json
   - runtime/title_candidates.json
   - runtime/title_shortlist_prompt.txt
2. 然后为本轮输入补齐这 3 个关键结果文件：
   - runtime/title_shortlist_result.json
   - runtime/draft_result.json
   - runtime/top10_ranking_result.json
3. 之后继续 apply 正式链路，生成：
   - runtime/shortlist.json
   - runtime/draft_input.json
   - runtime/drafted_items.json
   - runtime/top10_ranking_input.json
   - runtime/top10_publishable.json
   - runtime/dashboard.html
4. 执行：
   - ./scripts/serve_dashboard_8510.sh

请不要复用旧的占位结果文件，不要继续使用 [TEST] 占位摘要。
如果 title_shortlist_result.json、draft_result.json、top10_ranking_result.json 没有为当前这一轮输入正确生成，就不要假装正式页面已经完成。

完成后告诉我：
1. runtime/top10_publishable.json 是否存在，count 是否为 10
2. runtime/dashboard.html 是否已更新
3. scripts/check_runtime_status.py 是否通过
4. summary_placeholders 是否为空
5. 8510 页面是否指向 Assistant，而不是 Manager
```

> 关键判断：不要把“脚本跑成功”误当成“正式早报已经可交付”。必须确认当前这轮输入对应的 shortlist / draft / ranking 结果都已生成，并产出无占位摘要的正式页面。

---

## 4. 放行页面端口 8510（手动）

页面链接当前使用：

```text
http://101.47.152.44:8510/dashboard.html
```

其中 `8510` 是早报页面端口，需要在云控制台和服务器侧同时放行。

### 4.1 火山云安全组放行

操作路径：

```text
火山云控制台
-> 云服务器 ECS
-> 找到对应服务器实例
-> 安全组
-> 入方向规则
-> 添加规则
```

填写规则：

| 项目 | 填写 |
|---|---|
| 策略 | 允许 |
| 协议类型 | TCP |
| 源地址 | `0.0.0.0/0`，或只允许固定 IP |
| 端口范围 | `8510` |
| 描述 | Morning Newspaper Assistant dashboard |

### 4.2 服务器防火墙放行

如果服务器启用了 `ufw`，发送给龙虾或自己在服务器执行：

```bash
sudo ufw allow 8510/tcp
```

如果服务器使用 `firewalld`，执行：

```bash
sudo firewall-cmd --permanent --add-port=8510/tcp
sudo firewall-cmd --reload
```

如果以后端口从 `8510` 改成 `8520`，下面四处要一起改：

```text
火山云安全组端口
服务器防火墙端口
静态服务监听端口
最终页面链接里的端口
```

---

## 5. 启动页面服务（发给龙虾）

发送：

```text
请启动 Morning-Newspaper-Assistant 的早报页面服务。

执行：
cd /root/projects/Morning-Newspaper-Assistant
./scripts/serve_dashboard_8510.sh

完成后请确认：
1. 服务是否监听 0.0.0.0:8510
2. runtime/dashboard.html 是否存在
3. http://101.47.152.44:8510/dashboard.html 是否可以访问
4. 当前 8510 页面是否确实指向 Assistant 页面，而不是旧 Manager 页面
```

如果页面打不开，按顺序排查：

| # | 检查项 |
|---|---|
| 1 | `./scripts/serve_dashboard_8510.sh` 是否执行过 |
| 2 | 静态服务是否正在监听 `0.0.0.0:8510` |
| 3 | 火山云安全组是否放行 `8510` |
| 4 | 服务器本机防火墙是否放行 `8510` |
| 5 | `runtime/dashboard.html` 是否存在 |
| 6 | 页面是否是最新生成时间对应的版本 |
| 7 | 当前 `8510` 是否确实指向 Assistant，而不是旧 Manager |

---

## 6. 设置每日定时任务（发给龙虾）

发送：

```text
请为 Morning-Newspaper-Assistant 设置每日定时任务：

1. 每天北京时间 07:55 自动运行正式早报生成流程，并完成质量校验
2. 每天北京时间 08:05 在当前渠道发送晨报摘要和页面链接

要求：
- 07:55 负责生成 + 校验
- 08:05 负责发送消息
- 不要把“生成成功”误当成“已经发出晨报”
- 失败时也必须在当前渠道发送失败通知

请完成后告诉我：
1. 定时任务配置在哪里
2. 07:55 任务会执行什么命令
3. 08:05 任务会执行什么发送动作
4. 失败通知会包含哪些信息
```

如果龙虾需要按 cron 理解，可以提醒它：

```text
07:55 生成正式页面并校验
08:05 向当前渠道发送晨报摘要和页面链接
```

---

## 7. 发送早报消息验证（发给龙虾）

正式产物生成后，发送：

```text
请从下面这个正式文件读取今日早报前三条：

/root/projects/Morning-Newspaper-Assistant/runtime/top10_publishable.json

发送前请先确认：
1. /root/projects/Morning-Newspaper-Assistant/runtime/dashboard.html 已更新
2. top10_publishable.json 中 count = 10
3. 页面没有大面积兜底摘要
4. 8510 页面已指向 Assistant

然后向当前渠道发送一条中文早报消息。消息必须包含：
1. 今日 AI 早报已更新
2. 前三条看点：每条包含标题和一句话摘要
3. 完整页面链接：http://101.47.152.44:8510/dashboard.html

发送要求：
- 发到当前渠道，不要换频道、不要另开对话、不要发到邮件
- 不要只发“今日 AI 早报已更新 + 链接”
- 必须带前三条标题和一句话摘要
```

建议最终消息格式固定为：

```text
今日 AI 早报已更新

今日前三条：
1. <标题一>
   <一句话摘要一>
2. <标题二>
   <一句话摘要二>
3. <标题三>
   <一句话摘要三>

完整早报：
http://101.47.152.44:8510/dashboard.html
```

---

## 8. 失败通知验证（发给龙虾）

发送：

```text
请确认 Morning-Newspaper-Assistant 的每日任务失败时，也会在当前渠道发送失败通知。

失败通知至少包含：
1. 失败发生在哪一步：collect / shortlist / draft / ranking / build_dashboard / quality
2. 关键报错摘要
3. 当前是否仍可继续查看旧版 dashboard
4. 需要人工处理的点

请不要静默失败，也不要只写日志不发当前渠道消息。
```

失败消息可以使用这个格式：

```text
今日 AI 早报生成失败

失败步骤：<collect / shortlist / draft / ranking / build_dashboard / quality>
错误摘要：<关键报错>
当前页面：<旧版 dashboard 是否仍可访问>
需要人工处理：<下一步处理建议>
```

---

## 9. 验收检查清单

- [ ] 龙虾已 clone / 更新完整的 `Morning-Newspaper-Assistant` 仓库
- [ ] Python 虚拟环境和依赖安装成功
- [ ] 正式链路生成了 `runtime/top10_publishable.json`
- [ ] `top10_publishable.json` 中 count = 10
- [ ] `runtime/dashboard.html` 已更新
- [ ] `scripts/check_runtime_status.py` 通过
- [ ] `summary_placeholders` 为空
- [ ] 页面没有 `[TEST]` 占位摘要
- [ ] `./scripts/serve_dashboard_8510.sh` 已启动页面服务
- [ ] `http://101.47.152.44:8510/dashboard.html` 能正常打开
- [ ] `8510` 页面只指向 Assistant，不指向 Manager
- [ ] 每天北京时间 07:55 能自动生成 + 校验
- [ ] 每天北京时间 08:05 能在当前渠道发送消息
- [ ] 消息里有前三条标题和一句话摘要
- [ ] 消息里有完整页面链接
- [ ] 失败时能在当前渠道说明失败原因

---

## 10. 常见问题速查

| 龙虾报的错 / 现象 | 原因 | 你发什么 |
|---|---|---|
| 只 clone 了 skill 子目录 | 没有拿完整仓库 | 「请 clone 完整 Morning-Newspaper-Assistant 仓库，不要只复制 skill 子目录」 |
| 页面里出现 `[TEST]` 摘要 | 复用了测试占位结果 | 「请重新为当前输入生成正式结果文件，不要复用旧占位文件」 |
| `top10_publishable.json` 不满 10 条 | ranking 或 publishable 生成不完整 | 「请检查 ranking 阶段，并确认 count = 10 后再发布」 |
| `dashboard.html` 没更新 | build_dashboard 未完成或写到旧目录 | 「请确认 dashboard 写入 Assistant 的 runtime 目录」 |
| 8510 页面还是旧内容 | 服务指向了 Manager 或旧目录 | 「请确认 8510 只服务 Morning-Newspaper-Assistant/runtime/dashboard.html」 |
| 脚本成功但没发消息 | 生成任务和发送任务混在一起理解了 | 「请继续执行发送动作，把前三条和链接发到当前渠道」 |
| 页面打不开 | 云安全组或服务器防火墙未放行 | 「请检查 8510 安全组、防火墙和服务监听状态」 |
| `missing IMAP_USER` | 未配置邮箱账号 | 「如果不接邮箱请跳过邮件源；如果接邮箱请配置 .env」 |
| IMAP 登录失败 | 用了邮箱登录密码而不是授权码 | 「请使用 163 邮箱客户端授权码作为 IMAP_PASS」 |

---

## 实验记录

请记录你在实验过程中遇到的任何与预期不符的情况：

| # | 发生在哪一步 | 预期行为 | 实际行为 | 你的解决方法 |
|---|------------|----------|---------|------------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

> 欢迎把你的实验记录和踩坑发现分享到课程社群。
