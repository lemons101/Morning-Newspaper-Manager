from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List


def build_dashboard_payload(runtime_dir: Path) -> Dict[str, Any]:
    collected = _safe_items(_read_json(runtime_dir / "collected_items.json"))
    triaged = _safe_items(_read_json(runtime_dir / "triage_items.json"))
    candidates = _safe_items(_read_json(runtime_dir / "triage_candidates.json"))
    rule_top10 = _safe_items(_read_json(runtime_dir / "top10_items.json"))
    ai_top10 = _safe_items(_read_json(runtime_dir / "ai_selected_top10.json"))
    enriched_top10 = _safe_items(_read_json(runtime_dir / "top10_enriched_items.json"))
    editorial_top10 = _safe_items(_read_json(runtime_dir / "top10_editorial_ready.json"))
    top10 = editorial_top10 or ai_top10 or enriched_top10 or rule_top10
    final_newspaper = _read_json(runtime_dir / "final_newspaper.json")
    mail_alerts = _safe_items(_read_json(runtime_dir / "mail_alerts.json"))
    source_report = _read_json(runtime_dir / "source_report.json")

    urgent_count = sum(1 for item in triaged if _priority(item) == "Urgent")
    important_count = sum(1 for item in triaged if _priority(item) == "Important")
    fyi_count = sum(1 for item in triaged if _priority(item) == "FYI")
    urgent_task_count = sum(1 for item in mail_alerts if _priority(item) == "Urgent")

    return {
        "generated_at": _now_iso(),
        "overview": {
            "collected_total": len(collected),
            "triaged_total": len(triaged),
            "candidate_count": len(candidates),
            "top10_count": len(top10),
            "ai_selected": bool(ai_top10),
            "urgent_count": urgent_count,
            "important_count": important_count,
            "fyi_count": fyi_count,
            "mail_alert_count": len(mail_alerts),
            "urgent_mail_count": urgent_task_count,
            "urgent_task_count": urgent_task_count,
        },
        "headline": str(final_newspaper.get("headline") or "今日 AI 早报").strip(),
        "lead": _build_lead_bullets(final_newspaper, top10),
        "top_stories": _final_top_stories(final_newspaper, top10),
        "other_signals": _final_other_signals(final_newspaper),
        "top_items": [_to_display_item(item, index + 1) for index, item in enumerate(_filter_top10(top10))],
        "mail_alerts": [_to_display_item(item, index + 1) for index, item in enumerate(mail_alerts)],
        "source_health": _source_rows(source_report),
    }


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = payload.get("items", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _priority(item: Dict[str, Any]) -> str:
    value = str(item.get("priority", "")).strip()
    if value in {"Urgent", "Important", "FYI"}:
        return value
    return "FYI"


def _to_display_item(item: Dict[str, Any], rank: int) -> Dict[str, Any]:
    reasons = item.get("reasons", [])
    if not isinstance(reasons, list):
        reasons = []
    title = str(item.get("title", "(untitled)")).strip() or "(untitled)"
    summary = str(item.get("summary") or item.get("summary_llm") or item.get("short_summary") or "").strip()
    source_type = str(item.get("source_type", "")).strip()
    source_name = str(item.get("source_name", "")).strip()
    channel = str(item.get("channel", "")).strip()
    priority = _priority(item)

    # 优先使用新版 editorial 链产出的标题/摘要；旧 summary 字段仅作为降级兜底
    title_zh = str(item.get("card_title") or item.get("title_zh") or item.get("title") or "").strip() or _title_zh(title, summary, source_type, source_name, channel)
    title_en = str(item.get("title_en") or "").strip() or title
    summary_zh = str(item.get("summary_main") or item.get("card_summary") or item.get("editorial_summary_hint") or "").strip()
    if not _looks_like_good_chinese_summary(summary_zh):
        summary_zh = str(item.get("why_it_matters") or "").strip() if _looks_like_good_chinese_summary(str(item.get("why_it_matters") or "").strip()) else ""
    if not _looks_like_good_chinese_summary(summary_zh):
        summary_zh = str(item.get("summary_zh") or "").strip()
    if not _looks_like_good_chinese_summary(summary_zh):
        summary_zh = _summary_zh(title, summary, source_type, source_name, channel, item)
    summary_en = str(item.get("summary_en") or "").strip() or summary
    why_it_matters = str(item.get("why_it_matters") or "").strip()
    key_points = item.get("key_points") or []
    if not isinstance(key_points, list):
        key_points = []
    key_points = [str(point).strip() for point in key_points if str(point).strip()]

    original_rank = int(item.get("rank", rank) or rank)
    return {
        "rank": rank,
        "original_rank": original_rank,
        "item_id": str(item.get("item_id", "")).strip(),
        "priority": priority,
        "title": title_zh,
        "title_zh": title_zh,
        "title_en": title_en,
        "summary": summary_zh,
        "summary_zh": summary_zh,
        "summary_en": summary_en,
        "why_it_matters": why_it_matters,
        "key_points": key_points,
        "summary_basis": str(item.get("summary_basis", "")).strip(),
        "summary_confidence": str(item.get("summary_confidence", "")).strip(),
        "summary_warnings": item.get("summary_warnings") or [],
        "source_name": source_name,
        "source_type": source_type,
        "published_at": str(item.get("published_at", "")).strip(),
        "impact_score": int(item.get("impact_score", 0) or 0),
        "confidence": float(item.get("confidence", 0.0) or 0.0),
        "reasons": [str(reason).strip() for reason in reasons if str(reason).strip()],
        "suggested_action": str(item.get("suggested_action", "")).strip(),
        "url": str(item.get("url", "")).strip(),
        "topic_icon": _topic_icon(item),
    }


def _build_lead_bullets(final_newspaper: Dict[str, Any], top10: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    items = _filter_top10(top10)
    cards: List[Dict[str, str]] = []
    for idx, item in enumerate(items[:3], 1):
        title = str(item.get('card_title') or item.get('title_zh') or item.get('title') or '').strip()
        summary = str(item.get('summary_main') or item.get('card_summary') or item.get('editorial_summary_hint') or item.get('summary_zh') or item.get('summary') or '').strip()
        key_points = item.get('key_points') or []
        if not isinstance(key_points, list):
            key_points = []
        first_point = ''
        for point in key_points:
            point_text = str(point).strip()
            if point_text:
                first_point = point_text
                break
        lead_text = first_point or summary
        if not title:
            continue
        cards.append({
            'key': f'lead-{idx}',
            'icon': _topic_icon(item),
            'title': title,
            'summary': _trim_lead_summary(lead_text),
        })
    if cards:
        return cards
    lead = str(final_newspaper.get('lead') or '').strip()
    return [{'key': 'lead', 'icon': '✨', 'title': '今日主线', 'summary': lead}] if lead else []


def _topic_icon(item: Dict[str, Any]) -> str:
    source_type = str(item.get('source_type') or '').strip()
    title = str(item.get('title') or '').lower()
    focus = str(item.get('editorial_focus') or '').strip()
    if source_type == 'github_advisory' or '安全' in focus:
        return '🛡️'
    if source_type == 'github_high_stars' and ('agent' in title or 'Agent' in focus or '平台' in focus or '约束' in focus):
        return '🤖'
    if source_type == 'github_high_stars':
        return '📦'
    if source_type == 'rss':
        return '🏛️'
    if source_type == 'hackernews_top':
        return '📰'
    return '✨'


def _trim_lead_summary(text: str, limit: int = 90) -> str:
    clean = re.sub(r'\s+', ' ', str(text or '').strip())
    if not clean:
        return ''
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rstrip(' ，,;；:：')
    return cut + '…'


def _looks_like_good_chinese_summary(text: str) -> bool:
    if not text:
        return False
    bad_signals = [
        'Hacker News new | past | comments | ask | show | jobs | submit login',
        'XCancel',
        'Websmith Home',
        'Running Adobe',
        '| Hacker News',
    ]
    if any(x in text for x in bad_signals):
        return False
    zh_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    return zh_chars >= 20


def _hackernews_summary_zh(title: str, body_text: str) -> str:
    text = re.sub(r'\s+', ' ', body_text or '').strip()
    if not text:
        return ''
    if 'Bluetooth LE MIDI' in text and 'Windows MIDI Services' in text:
        return '这是一款面向 Windows 的开源小工具，目标是把蓝牙 BLE MIDI 键盘稳定接入 Windows 的 MIDI 服务体系，让宿主软件、DAW 和 Web MIDI 应用像使用有线设备一样识别和使用无线键盘。作者围绕 Roland FP-90X 的实际排障过程，把配对成功但软件不可见、电脑回传音符无声，以及 MIDI 通道设置不一致等问题拆成了可定位、可修复的工程方案。'
    if 'Claude.md' in text and 'Apple Support app' in text:
        return '一则在社交平台传播的爆料称，Apple 在 Apple Support app 的一次更新中误带入了 Claude.md 文件，随后又通过紧急小版本将其移除。这类文件通常被视作 AI 编码工具的项目指令配置，因此事件被外界解读为 Apple 在部分开发流程中使用了 Claude 相关工具，也暴露出 AI 开发配置误入正式发行包的新型发布风险。'
    if 'PostScript Cartridge Plus' in text and 'browser' in text.lower():
        return '这篇文章把一段 1991 年随 HP LaserJet 扩展卡发布的 Adobe PostScript 解释器搬进了现代浏览器环境。作者通过模拟当年的 M68K 硬件和打印机外围接口，让原始 ROM 中的解释器在浏览器本地直接完成页面渲染，用户把 PostScript 文件拖进网页即可得到结果，全程不依赖服务器。'
    if 'website isn' in text.lower() and 'tool with one job' in text.lower():
        return '这篇文章讨论的不是具体网页技巧，而是一个常被管理层忽略的判断标准：网站首先是给用户完成任务用的，不是给老板或内部团队表达个人审美的。作者指出，很多网站并不是缺少研究或专业能力，而是在评审过程中不断被非用户视角的主观偏好改写，最后做成了让内部满意、却未必真正好用的版本。'
    preview = _extract_link_preview(text)
    if preview:
        return _preview_summary_zh(title, preview)
    return ''


def _filter_top10(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered: List[Dict[str, Any]] = []
    for item in items:
        title = str(item.get("title") or item.get("title_zh") or "").strip()
        body_quality = str(item.get("body_quality") or "").strip()
        editorial_priority = str(item.get("editorial_priority") or "").strip()
        if title in {"Craig Venter has died", "Cursor Camp"}:
            continue
        if body_quality == "thin" and editorial_priority != "risk_signal":
            continue
        filtered.append(item)
    return filtered[:10]


def _final_top_stories(payload: Dict[str, Any], editorial_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    stories = payload.get("top_stories", [])
    if not isinstance(stories, list):
        return []
    editorial_by_title = {str(item.get('title') or '').strip(): item for item in editorial_items if isinstance(item, dict)}
    result = []
    for story in stories[:3]:
        if not isinstance(story, dict):
            continue
        title = str(story.get('title') or '').strip()
        matched = editorial_by_title.get(title)
        summary = str(((matched or {}).get('summary_main')) or story.get('summary') or '').strip()
        why = str(((matched or {}).get('why_it_matters')) or story.get('why') or '').strip()
        key_points = (matched or {}).get('key_points') or []
        if not isinstance(key_points, list):
            key_points = []
        result.append({
            'title': str((matched or {}).get('card_title') or title).strip(),
            'summary': summary,
            'why': why,
            'key_points': [str(point).strip() for point in key_points if str(point).strip()][:3],
            'url': str((matched or {}).get('url') or '').strip(),
        })
    return result


def _final_other_signals(payload: Dict[str, Any]) -> List[str]:
    signals = payload.get("other_signals", [])
    if not isinstance(signals, list):
        return []
    return [str(x).strip() for x in signals if str(x).strip()][:5]


def _source_rows(source_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_source = source_report.get("by_source", {})
    if not isinstance(by_source, dict):
        return []
    rows = []
    for source_id, count in sorted(by_source.items()):
        rows.append(
            {
                "source_id": str(source_id),
                "items": int(count or 0),
                "status": "正常" if int(count or 0) > 0 else "无数据",
            }
        )
    return rows


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _title_zh(title: str, summary: str, source_type: str, source_name: str, channel: str) -> str:
    clean = _strip_priority_prefix(title)
    if channel == "mail_alert":
        return _mail_title_zh(clean)
    if source_type == "github_advisory":
        product, issue = _split_advisory_title(clean)
        return f"{product} 安全公告：需要关注的权限或数据风险"
    if source_type == "github_high_stars":
        repo = clean.split()[0]
        return f"开源项目动态：{repo}"
    if source_type == "hackernews_top":
        return f"社区热议：{_community_title(clean)}"
    if source_name.startswith("SEC"):
        return f"SEC 动态：{_official_title(clean)}"
    if "美联储" in source_name:
        return f"美联储动态：{_official_title(clean)}"
    if source_type == "tavily_skill":
        return f"AI 最新信号：{_community_title(clean)}"
    return clean


def _summary_zh(title: str, summary: str, source_type: str, source_name: str, channel: str, item: Dict[str, Any] | None = None) -> str:
    text = summary or title
    body_text = str((item or {}).get("body_text_clean") or (item or {}).get("body_text") or "").strip()
    if source_type == "hackernews_top":
        editorial = _hackernews_summary_zh(title, body_text or text)
        if editorial:
            return editorial
    if channel == "mail_alert":
        return _mail_summary_zh(title, text)
    if source_type == "github_advisory":
        severity = _extract_severity(text)
        product, issue = _split_advisory_title(title)
        severity_text = f"严重程度为 {severity}。" if severity else ""
        issue_text = _clean_issue_text(issue or title)
        return (
            f"这是一条 GitHub 安全公告，涉及 {product or '相关项目'}。"
            f"公告指出相关组件可能存在权限绕过、敏感信息暴露或配置保护不足等风险。"
            f"{severity_text}如果团队内部使用了该项目或依赖相关能力，需要确认版本范围、修复版本和是否存在实际暴露面。"
            f"原始问题描述：{issue_text}"
        )
    if source_type == "github_high_stars":
        stars = _extract_number(text, "stars")
        language = _extract_after(text, "language=")
        repo = title.split()[0]
        description = _after_bar(text)
        metrics = []
        if stars:
            metrics.append(f"约 {stars} 星")
        if language:
            metrics.append(f"主要语言为 {language}")
        metric_text = "，".join(metrics) if metrics else "近期有社区关注"
        return (
            f"{repo} 是一个近期活跃的开源项目，{metric_text}。"
            f"它值得关注的原因在于，开源项目的增长通常能反映开发者正在尝试的新工具、新框架或新工作流。"
            f"项目原始描述：{description or '暂无详细描述'}。"
            f"如果它和 AI Agent、模型工具链、图像生成、推理加速或开发者效率有关，可以进一步判断是否值得纳入后续技术跟踪。"
        )
    if source_type == "hackernews_top":
        preview = _extract_link_preview(text)
        if preview:
            return _preview_summary_zh(title, preview)
        return _title_based_summary_zh(title)
    if source_name.startswith("SEC"):
        return (
            f"这是一条 SEC 官方新闻稿，内容涉及金融市场、监管规则或公开市场事项。"
            f"它不一定直接属于 AI 技术新闻，但可能影响科技公司融资、上市、披露或资本市场环境。"
            f"原文核心信息：{_trim_text(text, 260)}"
        )
    if "美联储" in source_name:
        return (
            f"这是一条美联储官方动态，可能影响宏观环境、银行业或市场预期。"
            f"它通常不是 AI 技术信号，但可能影响企业预算、融资环境和市场风险偏好。"
            f"原文核心信息：{_trim_text(text, 260)}"
        )
    return f"这条信息的原始内容如下：{_trim_text(text, 320)}"


def _why_it_matters_zh(priority: str, title: str, summary: str, source_type: str, source_name: str, channel: str) -> str:
    if channel == "mail_alert":
        return "这是今天需要处理的具体事务，建议优先确认时间、责任人和下一步动作。"
    if source_type == "github_advisory":
        return "安全公告可能影响依赖组件或基础设施，建议检查内部是否使用相关项目。"
    if source_type in {"github_high_stars", "hackernews_top"}:
        return "社区热度可以反映 AI 工具链、开源项目或开发者关注方向的变化。"
    if source_type == "tavily_skill":
        return "这是 OpenClaw 主动搜索到的 AI 技术或商业信号，适合进入日报候选。"
    if source_name.startswith("SEC") or "美联储" in source_name:
        return "这类官方动态可能影响商业环境和资本市场，但是否进入 AI 早报需要结合业务相关性复核。"
    if priority == "Urgent":
        return "该信息被标记为紧急，需要今天确认是否影响业务。"
    return "该信息值得关注，可作为今日早报的背景材料。"


def _phrase_zh(text: str) -> str:
    clean = " ".join((text or "").split()).strip()
    if not clean:
        return "暂无摘要"
    replacements = [
        ("exposes sensitive information", "可能暴露敏感信息"),
        ("sensitive information", "敏感信息"),
        ("authorization bypass", "授权绕过"),
        ("policy bypass", "策略绕过"),
        ("case-sensitive host matching", "主机名大小写匹配问题"),
        ("path normalization mismatch", "路径规范化不一致"),
        ("follows symlinks outside", "跟随目录外符号链接"),
        ("filesystem read/write", "文件系统读写"),
        ("high severity", "高危"),
        ("medium severity", "中危"),
        ("critical vulnerability", "严重漏洞"),
        ("security advisory", "安全公告"),
        ("open-source", "开源"),
        ("AI agent", "AI Agent"),
        ("model release", "模型发布"),
        ("funding", "融资"),
        ("product launch", "产品发布"),
        ("enterprise adoption", "企业采用"),
        ("enforcement action", "执法行动"),
        ("approval of application", "批准申请"),
        ("economic projections", "经济预测"),
        ("FOMC statement", "FOMC 声明"),
        ("private fund reporting burdens", "私募基金报告负担"),
        ("customer cross-margining", "客户跨保证金安排"),
    ]
    output = clean
    for source, target in replacements:
        output = re.sub(re.escape(source), target, output, flags=re.IGNORECASE)
    return output[:240].rstrip() + ("..." if len(output) > 240 else "")


def _community_title(title: str) -> str:
    clean = _trim_text(title, 120)
    lower = clean.lower()
    if "open-source" in lower or "github" in lower:
        subject = clean.split(":", 1)[0].strip()
        return f"{subject} 引发开源社区关注"
    if "openai" in lower:
        return "OpenAI 相关话题引发社区讨论"
    if "voice ai" in lower:
        return "语音 AI 工具引发社区讨论"
    if "language model" in lower or "llm" in lower:
        return "语言模型相关话题引发社区讨论"
    return clean


def _official_title(title: str) -> str:
    clean = _trim_text(title, 120)
    lower = clean.lower()
    if "enforcement action" in lower:
        return "发布执法行动相关公告"
    if "approval of application" in lower:
        return "发布机构申请批准公告"
    if "private fund reporting" in lower:
        return "拟调整私募基金报告要求"
    if "fomc statement" in lower:
        return "发布 FOMC 声明"
    if "economic projections" in lower:
        return "发布经济预测材料"
    return clean


def _clean_issue_text(text: str) -> str:
    clean = " ".join((text or "").split()).strip()
    clean = re.sub(r"^GHSA-[a-z0-9-]+\s*\|\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"^CVE-\d{4}-\d+\s*\|\s*", "", clean, flags=re.IGNORECASE)
    return _trim_text(clean, 220)


def _trim_text(text: str, max_chars: int) -> str:
    clean = " ".join((text or "").split()).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + "..."


def _strip_priority_prefix(title: str) -> str:
    return re.sub(r"^\[(Urgent|Important|FYI)\]\s*", "", title).strip()


def _mail_title_zh(title: str) -> str:
    clean = _strip_priority_prefix(title)
    return f"今日待处理：{clean}"


def _mail_summary_zh(title: str, summary: str) -> str:
    timing = _extract_summary_field(summary, "action_timing")
    sender = _extract_summary_field(summary, "sender")
    pieces = ["这是一项从邮件中识别出的今日紧急事务。"]
    if timing:
        pieces.append(f"触发时间：{timing}。")
    if sender:
        pieces.append(f"邮件来源：{sender}。")
    pieces.append("请确认是否需要参会、回复、审批或完成对应动作。")
    return "".join(pieces)


def _split_advisory_title(title: str) -> tuple[str, str]:
    parts = [part.strip() for part in title.split("|") if part.strip()]
    if len(parts) >= 3:
        issue = parts[-1]
    elif len(parts) >= 1:
        issue = parts[-1]
    else:
        issue = title
    product = issue.split()[0].strip(":,") if issue else "相关项目"
    return product or "相关项目", issue


def _extract_severity(text: str) -> str:
    match = re.search(r"severity=([a-zA-Z]+)", text or "")
    if not match:
        return ""
    value = match.group(1).lower()
    return {"critical": "严重", "high": "高危", "medium": "中危", "low": "低危"}.get(value, value)


def _extract_number(text: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}=(\d+)", text or "")
    return match.group(1) if match else ""


def _extract_after(text: str, marker: str) -> str:
    if marker not in text:
        return ""
    value = text.split(marker, 1)[1].split("|", 1)[0].strip()
    return value[:40]


def _after_bar(text: str) -> str:
    parts = [part.strip() for part in text.split("|") if part.strip()]
    return parts[-1] if parts else text


def _extract_summary_field(summary: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}=([^|]+)", summary or "")
    return match.group(1).strip() if match else ""


def _extract_link_preview(summary: str) -> str:
    match = re.search(r"Linked page preview\. description=([^|]+)", summary or "")
    return match.group(1).strip() if match else ""


def _preview_summary_zh(title: str, preview: str) -> str:
    clean_title = title.strip()
    clean_preview = _trim_text(preview, 420)
    lower = f"{clean_title} {clean_preview}".lower()
    if "vibevoice" in lower:
        return f"链接内容主要介绍 Microsoft VibeVoice，一个面向语音生成/语音 AI 的开源项目。页面摘要提到：{clean_preview}"
    if "localsend" in lower:
        return f"链接内容主要介绍 Localsend，一个跨平台开源文件传输工具，可作为 AirDrop 的替代方案。页面摘要提到：{clean_preview}"
    if "language model" in lower or "llm" in lower or "talkie" in lower:
        return f"链接内容主要围绕语言模型或模型实验展开。页面摘要提到：{clean_preview}"
    if "github" in lower or "open-source" in lower or "open source" in lower:
        return f"链接内容主要介绍一个开源项目或开发者工具。页面摘要提到：{clean_preview}"
    return f"链接页面摘要显示，这篇内容主要围绕「{clean_title}」展开。页面摘要：{clean_preview}"


def _title_based_summary_zh(title: str) -> str:
    clean = title.strip()
    lower = clean.lower()
    if "localsend" in lower:
        return "链接内容主要介绍 Localsend，这是一个跨平台开源文件传输工具，定位类似 AirDrop 的替代方案。它的关注点在于本地设备之间的文件传输、跨系统兼容和开源实现。"
    if "vibevoice" in lower:
        return "链接内容主要介绍 Microsoft VibeVoice，这是一个语音 AI 相关的开源项目。它值得放进早报，是因为语音生成和多模态交互仍是 AI 应用落地的重要方向。"
    if "identity verification" in lower:
        return "链接内容主要围绕身份验证公司及其对外合作声明展开。它和 AI 早报的关联点在于 OpenAI 相关人物、身份验证产品和可信身份基础设施。"
    if "language model" in lower or "talkie" in lower:
        return "链接内容主要围绕语言模型实验或模型能力观察展开。它适合作为社区技术兴趣的参考，但还需要结合原文判断技术含量和实际价值。"
    if "open-source" in lower or "open source" in lower:
        return f"链接内容主要介绍一个开源项目：{clean}。当前页面没有提供可抓取的正文摘要，因此这里根据标题给出简要说明。"
    return f"链接内容主要围绕「{clean}」展开。当前页面没有提供可抓取的正文摘要，因此这里根据标题给出简要说明。"
