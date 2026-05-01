# LLM 主导粗筛（15 条候选池）落地方案

## 目标
将当前 `triage_items -> select_triage_candidates` 的机械排序粗筛，升级为 **LLM 主导的候选池判断**。

目标不是直接选 Top10，而是先从去重后的新闻条目中挑出更高质量的 15 条候选池。

---

## 当前链路

```text
collect_fixed_platforms + collect_openclaw_tavily
-> deduplicate_items
-> triage_items
-> select_triage_candidates(limit=15)
-> select_top_items(limit=10)
-> enrich top_items
-> ai_triage
-> newspaper_writer
-> dashboard
```

当前 `select_triage_candidates` 规则：
- 排除 `mail_alert`
- 按 `priority -> impact_score -> confidence -> published_at` 排序
- 截前 15 条

这一步没有真正利用 LLM 的编辑判断能力。

---

## 新链路（推荐）

```text
deduped news items
-> triage_items (保留作基础字段)
-> llm_candidate_triage
-> triage_items_llm_scored.json
-> select_triage_candidates_by_llm(limit=15)
-> triage_candidates.json
-> select_top_items(limit=10)
-> 后续正文增强 / editorial-ready / dashboard
```

核心变化：
- 候选池 15 条由 LLM 主导判断
- 旧 triage 保留但不再主导候选池排序

---

## LLM 输入字段
每条候选建议输入：
- `item_id`
- `title`
- `source_name`
- `source_type`
- `url`
- `published_at`
- `priority`（旧规则产物，仅作参考）
- `impact_score`
- `confidence`
- `summary`
- `summary_llm`
- `body_fetch_status`
- `summary_basis`
- `reasons`
- `热度信号`：
  - HN: score/comments
  - GitHub: stars/forks
  - Advisory: severity
  - 官方来源 / RSS 标识

---

## LLM 输出 schema

```json
{
  "item_id": "sha1:xxx",
  "priority_llm": "Urgent",
  "candidate_score": 9,
  "quality_score": 4,
  "ai_relevance_score": 5,
  "heat_score": 4,
  "final_keep": "yes",
  "editorial_reason": "这条直接反映了 AI Agent 工具链的重要新进展，热度与相关性都高，适合进入候选池前列。"
}
```

字段说明：
- `priority_llm`: `Urgent | Important | FYI`
- `candidate_score`: 1~10，综合候选价值
- `quality_score`: 1~5，信息密度/正文质量
- `ai_relevance_score`: 1~5，和 AI 主线的相关性
- `heat_score`: 1~5，热度/传播势能/社区关注度
- `final_keep`: `yes | no`
- `editorial_reason`: 一句话说明保留/淘汰原因

---

## 粗筛 Prompt 目标
Prompt 不是让模型“写摘要”或“选 Top10”，而是只做：

> 判断这条是否值得进入今天 AI 晨报的 15 条候选池。

模型需要综合考虑：
- AI 相关性
- 新闻价值
- 信息密度
- 热度 / 传播势能
- 来源可信度
- 时效性

模型必须直接输出 JSON。

---

## 候选池排序逻辑
候选池排序建议改成：

1. `final_keep == yes`
2. `priority_llm` (`Urgent > Important > FYI`)
3. `candidate_score`
4. `heat_score`
5. `quality_score`
6. `ai_relevance_score`
7. `published_at`

最后取前 15 条。

---

## 保留旧 triage 的方式
旧 triage 先不删：
- 继续输出 `priority`
- 作为 debug / fallback 字段
- 不再主导候选池排序

这样可以在新链路不稳定时快速回退。

---

## 推荐代码改造点

### 1. 新增函数
- `run_llm_candidate_triage(root: Path) -> Path`
- `select_triage_candidates_by_llm(items: Iterable[dict], limit: int = 15) -> List[dict]`

### 2. 复用文件
- `src/pipeline/ai_triage.py`
  - 复用 `openclaw infer model run` 调用骨架
  - 但新建候选池 triage 逻辑，避免和 Top10 摘要混在一起

### 3. collect.py 插入点
当前：
- `triage_items`
- `select_triage_candidates`

新链路：
- `triage_items`
- `run_llm_candidate_triage`
- `select_triage_candidates_by_llm`

---

## 分阶段落地建议

### Phase 1
- 先产出 `triage_items_llm_scored.json`
- 先不改 Top10 和 dashboard
- 只替换候选池 15 条的选择方式

### Phase 2
- 对比：旧候选池 vs 新候选池
- 观察几轮结果是否更接近编辑预期

### Phase 3
- 再考虑把 7:3 配比接到 Top10 选择层

---

## 成功标准
- `triage_candidates.json` 仍是 15 条
- 但质量明显提升：
  - AI 主线更聚焦
  - 弱相关/噪音项更少
  - 热度高且值得看的内容更容易进候选池
- 下游 Top10 成稿质量提升
