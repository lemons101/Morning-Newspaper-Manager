# 运行、自动化与维护说明

## 1. 日常运行

### 1.1 手动跑完整晨报链

```bash
cd /root/projects/Morning-Newspaper-Manager
python3 src/pipeline/collect.py --project-root /root/projects/Morning-Newspaper-Manager
```

这会完成：

- 多来源采集
- 去重
- triage
- Top10
- ai_triage
- 正文增强
- editorial-ready
- `dashboard.html` 生成

### 1.2 手动跑每日晨报脚本

```bash
cd /root/projects/Morning-Newspaper-Manager
./scripts/run_daily_newspaper.sh
```

这个脚本适合：

- 定时任务
- 快速重跑
- 手动验证当天 HTML 是否能重新生成

---

## 2. 看结果应该看哪里

### 最终页面

- `runtime/dashboard.html`

### 最终成稿

- `runtime/final_newspaper.json`
- `runtime/final_newspaper.md`

### 最关键中间层

- `runtime/top10_editorial_ready.json`

### 上游候选与增强结果

- `runtime/top10_items.json`
- `runtime/top10_enriched_items.json`
- `runtime/triage_candidates.json`

---

## 3. 当前自动化任务

### 3.1 每日 08:00 自动更新页面
任务目标：

- 重跑整条晨报生成链
- 覆盖当天 `runtime/dashboard.html`

### 3.2 每日 08:05 自动推送给用户
推送内容：

- 今日晨报已更新
- 3 条今日看点
- 固定链接

固定链接：

- `http://101.47.152.44:8510/dashboard.html`

---

## 4. 当前展示入口

### 主入口

- `http://101.47.152.44:8510/dashboard.html`

这是当前最稳定、最适合手机和外部访问的入口。

### 本地产物文件

- `/root/projects/Morning-Newspaper-Manager/runtime/dashboard.html`

---

## 5. 常见问题排查

### 5.1 页面能打开，但内容没变
优先检查：

1. 是否真的重新运行了生成链
2. `runtime/dashboard.html` 的更新时间是否变化
3. `top10_editorial_ready.json` 是否变化
4. 页面是否缓存了旧内容

### 5.2 页面结构对了，但内容像老版本
这通常意味着展示层重新退回了旧摘要字段。

优先检查：

- `view_model.py` 是否优先吃 `card_title` / `card_summary`
- 页面是否又优先展示 `summary_zh`

### 5.3 页面内容很短、像 metadata dump
优先检查：

- `top10_enriched_items.json` 的正文抓取质量
- `top10_editorial_ready.json` 是否有合适的 `card_summary`
- 来源正文是否本身就很弱

### 5.4 8510 链接能在电脑打开，但手机不稳
优先检查：

- 服务是否绑定 `0.0.0.0`
- 8510 是否真正对外开放
- 公网 / 防火墙 / 安全组是否放行
- 是否误用了本地地址或 tailnet 地址

### 5.5 明天打开还是昨天内容
如果自动更新没有成功，就会继续显示旧 HTML。

优先检查：

- 每日 08:00 任务是否执行
- 执行时是否报错
- `runtime/dashboard.html` 是否被新的生成结果覆盖

---

## 6. 改造时的推荐顺序

如果要继续改造这套系统，建议顺序如下：

1. 先确认 runtime 产物稳定
2. 再优化 `top10_editorial_ready.json`
3. 再优化页面展示
4. 再优化分享访问链路
5. 最后再扩更多自动化和推送

---

## 7. 当前明确不建议的做法

### 不建议 1：直接回退旧 summary 展示链
这样会让页面快速回到“老版本味道”。

### 不建议 2：把项目内嵌模型成稿重新当主路径
当前环境里这条链已验证不稳。

### 不建议 3：一开始就大改采集架构
当前更重要的是稳住：

- runtime 产物
- editorial-ready 中间层
- dashboard.html 展示
- 每日自动更新/推送

---

## 8. 维护者应优先记住的 5 件事

1. `top10_editorial_ready.json` 是最关键的中间层。
2. `dashboard.html` 是当前主交付物。
3. 8510 是固定分享入口，不要轻易切换。
4. 这套系统现在是“按天覆盖更新”，不是历史归档系统。
5. 先稳住链路，再追求更复杂的生成与推送能力。
