# Morning Newspaper 定时早报交接文档

## 目标

目标很简单：让龙虾每天准时生成 AI 早报，并在**当前渠道**发出一条消息。消息中需要包含：

- 前三条看点
- 完整页面链接

整个事情分为两部分：

1. **龙虾负责**：拉取项目、按规则运行、定时生成早报、在当前渠道发送摘要和链接、失败时也要发失败说明。
2. **人工负责**：在火山云控制台和服务器侧放行页面端口，确保 `dashboard.html` 可以被公网访问。

---

## 一、给龙虾执行的部分

### 1. 总要求

龙虾需要完成以下事情：

- clone 完整仓库，而不是只拿某个 skill 子目录
- 在项目目录中初始化环境
- 每天北京时间 **08:00** 自动生成早报
- 生成成功后，读取正式产物里的前三条内容
- 在**当前渠道**发送一条中文晨报消息
- 如果当天生成失败，也必须在**当前渠道**说明失败原因
- 不要直接在正式发布链路上做实验性改动

### 2. 可直接发给龙虾的指令

```text
请从 GitHub 拉取并使用 Morning-Newspaper-Manager 项目，每天定时生成 AI 早报，并把结果发到当前渠道。

仓库地址：git@github.com:lemons101/Morning-Newspaper-Manager.git
HTTPS 备用地址：https://github.com/lemons101/Morning-Newspaper-Manager.git

注意：
- 必须 clone 完整仓库，不要只复制某个 skill 子目录。
- 可参考仓库中的 skill 目录，但如果仓库中的旧 skill 规则与当前正式运行规则不一致，请以项目 README、运行脚本和当前交付约束为准。
- 不要直接在正式发布链路上做 rewrite / prompt / display_rewrite 输入结构实验。

初始化步骤：
1. mkdir -p /root/projects
2. cd /root/projects
3. git clone git@github.com:lemons101/Morning-Newspaper-Manager.git
4. cd /root/projects/Morning-Newspaper-Manager
5. python3 -m venv .venv
6. source .venv/bin/activate
7. pip install -r requirements.txt
8. 如果要接入邮箱告警，请在仓库根目录配置 .env，填入 IMAP_USER 和 IMAP_PASS

默认项目目录是：/root/projects/Morning-Newspaper-Manager。
如果你把项目放在别的目录，请把下面所有命令里的 /root/projects/Morning-Newspaper-Manager 都替换成实际目录。

每日生成命令：
cd /root/projects/Morning-Newspaper-Manager
export MORNING_NEWSPAPER_PROJECT_ROOT=/root/projects/Morning-Newspaper-Manager
export DISPLAY_REWRITE_MODEL=hotai/gpt-5.4
bash scripts/run_daily_newspaper.sh /root/projects/Morning-Newspaper-Manager

请设置为每天北京时间 08:00 自动执行。

重要约束：
1. 正式产物默认包括：
   - /root/projects/Morning-Newspaper-Manager/runtime/top10_editorial_ready.json
   - /root/projects/Morning-Newspaper-Manager/runtime/final_newspaper.json
   - /root/projects/Morning-Newspaper-Manager/runtime/dashboard.html
2. 不要直接修改正式发布链路中的 prompt、display_rewrite 输入结构、summary 字段优先级，除非已经先在实验输出中验证通过。
3. 任何 rewrite / 展示层实验，必须先写到实验文件或实验页面；只有在“页面效果更好 + 质量检查通过 + 审计检查通过”后，才能 promote 到正式产物。
4. 不要靠页面层隐藏 points、兜底摘要去掩盖内容层问题；内容问题优先在内容层修。
5. 页面中的发布时间字段应尽量补齐，不能长期大量显示 "-"。

注意：
- `scripts/run_daily_newspaper.sh` 负责生成 + 检查
- 生成成功后，必须再执行一次发送动作
- 不要把“脚本跑成功”误当成“已经发出晨报”

执行成功后，请从以下正式文件读取前三条：
/root/projects/Morning-Newspaper-Manager/runtime/top10_editorial_ready.json

发送前请确认：
- /root/projects/Morning-Newspaper-Manager/runtime/dashboard.html 已更新
- top10_editorial_ready.json 中 count = 10
- 页面没有大面积兜底摘要
- 发布时间字段尽量补齐，避免页面大量显示 "-"

然后向当前渠道发送一条中文早报消息。消息必须包含：
1. 今日 AI 早报已更新
2. 前三条看点：每条包含标题和一句话摘要
3. 完整页面链接：http://101.47.152.44:8510/dashboard.html

发送要求：
- 发到当前渠道，不要换频道、不要另开对话、不要发到邮件。
- 不要只发“今日 AI 早报已更新 + 链接”，必须带前三条标题和一句话摘要。
- 如果当天生成失败，也要在当前渠道说明失败原因和需要人工处理的点。

如果当天生成失败，也必须在当前渠道发送失败通知，至少包含：
1. 失败发生在哪一步（collect / display_rewrite / rebuild_dashboard / quality / audit）
2. 关键报错摘要
3. 当前是否仍可继续查看旧版 dashboard
```

### 3. 龙虾每日消息格式

建议固定为以下格式：

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

补充要求：

- 必须有**标题**
- 必须有**一句话摘要**
- 必须有**完整链接**
- 不能只发一句“已更新，请查看链接”

### 4. 定时任务建议

建议龙虾按每天北京时间 **08:00** 运行生成脚本。

如果需要 cron，可使用：

```cron
0 8 * * * cd /root/projects/Morning-Newspaper-Manager && MORNING_NEWSPAPER_PROJECT_ROOT=/root/projects/Morning-Newspaper-Manager DISPLAY_REWRITE_MODEL=hotai/gpt-5.4 bash scripts/run_daily_newspaper.sh /root/projects/Morning-Newspaper-Manager >> runtime/daily.log 2>&1
```

注意：

- 这条 cron 只负责**生成 + 质检**
- **消息发送是独立动作**
- 不要把“生成成功”误当成“已经在当前渠道发了晨报”

### 5. 龙虾侧最小验收标准

龙虾侧验收至少包括：

```text
每天北京时间 08:00 能自动运行早报生成命令
生成后能在当前渠道发送消息
消息里有前三条标题和摘要
消息里有完整页面链接
失败时能在当前渠道说明失败原因
正式页面没有大面积兜底摘要
页面发布时间字段不能长期大量显示 "-"
```

---

## 二、人工手动配置网页端口的部分

这部分**不是给龙虾的**，而是给人手动配置页面访问。

当前页面链接使用：

```text
http://101.47.152.44:8510/dashboard.html
```

其中 `8510` 是页面端口，需要在云控制台和服务器侧同时放行。

### 1. 火山云安全组放行 8510

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
| --- | --- |
| 策略 | 允许 |
| 协议类型 | TCP |
| 源地址 | `0.0.0.0/0`，或只允许固定 IP |
| 端口范围 | `8510` |
| 描述 | Morning Newspaper dashboard |

如果以后端口从 `8510` 改成 `8520`，以下四处都要一起改：

```text
火山云安全组端口
服务器防火墙端口
静态服务监听端口
最终页面链接里的端口
```

### 2. 服务器上启动静态页面服务

在服务器上运行：

```bash
cd /root/projects/Morning-Newspaper-Manager/runtime
python3 -m http.server 8510 --bind 0.0.0.0
```

### 3. 如果服务器防火墙开启，也要放行 8510

Ubuntu / Debian（ufw）：

```bash
sudo ufw allow 8510/tcp
```

CentOS / RHEL（firewalld）：

```bash
sudo firewall-cmd --permanent --add-port=8510/tcp
sudo firewall-cmd --reload
```

### 4. 页面可访问性检查

最终验收：

```text
http://101.47.152.44:8510/dashboard.html 能正常打开
```

如果打不开，优先依次检查：

1. 静态服务是否正在监听 `0.0.0.0:8510`
2. 云安全组是否放行 `8510`
3. 服务器本机防火墙是否放行 `8510`
4. 页面文件 `runtime/dashboard.html` 是否存在
5. 页面是否是最新生成时间对应的版本

---

## 三、补充说明

建议在交接时额外强调下面这句：

```text
注意：当前正式页已有一版稳定基线。后续优化应优先走实验产物验证，不要直接在正式发布页上做未验证改动。
```

这句话很重要，用于防止后续再次直接在正式链上试验，导致正式页面被跑坏。
