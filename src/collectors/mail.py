from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header
from email.message import Message
from email.policy import default
from email.utils import parsedate_to_datetime
import imaplib
import json
import os
import poplib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from src.collectors.common import positive_int
from src.models import CollectedItem, item_from_fields, make_item_id, utc_now_iso


def fetch_mail_alerts(
    source: Dict[str, Any],
    *,
    max_items: int,
    root: Path | None = None,
    runtime_config: Dict[str, Any] | None = None,
) -> List[CollectedItem]:
    username = _source_secret(source, "user_env", "IMAP_USER", "MAIL_USER")
    password = _source_secret(source, "pass_env", "IMAP_PASS", "MAIL_PASSWORD")
    source_id = str(source.get("id", "mailbox")).strip()
    if not username:
        print(f"[WARN] mail source skipped id={source_id}: missing user env")
        return []
    if not password:
        print(f"[WARN] mail source skipped id={source_id}: missing password env")
        return []

    queue_path = _queue_path(source, root=root, runtime_config=runtime_config or {})
    source = dict(source)
    source["_mail_queue_exists"] = queue_path.exists()
    queue = _load_event_queue(queue_path)

    try:
        alerts, events = _fetch_imap(source, username=username, password=password, max_items=max_items)
    except Exception as exc:
        print(f"[WARN] IMAP failed id={source_id}: {exc}")
        alerts = []
        events = []

    if not alerts and bool(source.get("pop3_fallback_enabled", False)):
        try:
            alerts, events = _fetch_pop3(source, username=username, password=password, max_items=max_items)
        except Exception as exc:
            print(f"[WARN] POP3 fallback failed id={source_id}: {exc}")

    queue = _merge_event_queue(queue, events)
    due_alerts, queue = _due_alerts_from_queue(source, queue)
    _save_event_queue(queue_path, queue)

    return _dedup_mail_alerts(alerts + due_alerts)[:max_items]


def _source_secret(source: Dict[str, Any], env_key: str, default_env: str, fallback_env: str) -> str:
    env_name = str(source.get(env_key, default_env)).strip() or default_env
    return os.getenv(env_name, "").strip() or os.getenv(fallback_env, "").strip()


def _fetch_imap(
    source: Dict[str, Any],
    *,
    username: str,
    password: str,
    max_items: int,
) -> Tuple[List[CollectedItem], List[Dict[str, Any]]]:
    host = str(source.get("host", "")).strip()
    port = positive_int(source.get("port"), 993)
    folders = source.get("folders", ["INBOX"])
    if not isinstance(folders, list) or not folders:
        folders = ["INBOX"]

    alerts: List[CollectedItem] = []
    events: List[Dict[str, Any]] = []
    with imaplib.IMAP4_SSL(host, port) as client:
        client.login(username, password)
        for folder in folders:
            status, _ = client.select(str(folder), readonly=True)
            if status != "OK":
                continue
            status, data = client.search(None, "ALL")
            if status != "OK" or not data:
                continue
            ids = data[0].split()
            max_messages = positive_int(source.get("max_messages"), 50)
            for msg_id in reversed(ids[-max_messages:]):
                status, fetched = client.fetch(msg_id, "(RFC822)")
                if status != "OK" or not fetched:
                    continue
                blob = _first_message_blob(fetched)
                if not blob:
                    continue
                item, event = _message_to_alert_and_event(source, blob)
                if item is not None:
                    alerts.append(item)
                if event is not None:
                    events.append(event)
    return _dedup_mail_alerts(alerts), _dedup_events(events)


def _fetch_pop3(
    source: Dict[str, Any],
    *,
    username: str,
    password: str,
    max_items: int,
) -> Tuple[List[CollectedItem], List[Dict[str, Any]]]:
    host = str(source.get("pop_host", "")).strip()
    port = positive_int(source.get("pop_port"), 995)
    max_messages = positive_int(source.get("max_messages"), 50)
    alerts: List[CollectedItem] = []
    events: List[Dict[str, Any]] = []

    client = poplib.POP3_SSL(host, port, timeout=20)
    try:
        client.user(username)
        client.pass_(password)
        _, lines, _ = client.list()
        count = len(lines)
        start = max(1, count - max_messages + 1)
        for index in range(count, start - 1, -1):
            _, msg_lines, _ = client.retr(index)
            blob = b"\n".join(msg_lines)
            item, event = _message_to_alert_and_event(source, blob)
            if item is not None:
                alerts.append(item)
            if event is not None:
                events.append(event)
    finally:
        try:
            client.quit()
        except Exception:
            pass
    return _dedup_mail_alerts(alerts), _dedup_events(events)


def _first_message_blob(fetched: Any) -> bytes | None:
    for part in fetched:
        if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], (bytes, bytearray)):
            return bytes(part[1])
    return None


def _message_to_alert_and_event(source: Dict[str, Any], blob: bytes) -> Tuple[CollectedItem | None, Dict[str, Any] | None]:
    message = message_from_bytes(blob, policy=default)
    received_dt = _parse_mail_datetime(message.get("Date"))
    lookback_hours = _mail_lookback_hours(source)
    if received_dt < datetime.now(timezone.utc) - timedelta(hours=lookback_hours):
        return None, None

    subject = _decode_mime_header(message.get("Subject")) or "(no subject)"
    sender = _decode_mime_header(message.get("From"))
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    if _is_ignored_sender(source, sender_lower) or _is_ignored_subject(source, subject_lower):
        return None, None
    message_id = _decode_mime_header(message.get("Message-ID"))
    body = _extract_text_body(message)
    action = _detect_action(source, subject=subject, body=body)
    event = _mail_event(source, sender=sender, subject=subject, body=body, message_id=message_id, received_dt=received_dt, action=action)
    due_action = action.get("label", "") if action.get("is_due") else ""
    priority, reason = _classify_mail(source, sender=sender, subject=subject, body=body, action_hit=due_action)
    if priority not in {"Urgent", "Important"}:
        return None, event

    source_id = str(source.get("id", "mailbox")).strip()
    source_name = str(source.get("name", source_id)).strip()
    summary = f"{priority} mail alert. reason={reason}"
    if sender:
        summary += f" | sender={sender}"
    if due_action:
        summary += f" | action_timing={due_action}"
    if body:
        summary += f" | {body[:240]}"

    url = f"mail:{message_id}" if message_id else f"mail:{source_id}:{subject}"
    return item_from_fields(
        channel="mail_alert",
        source_type="mail_alerts",
        source_id=source_id,
        source_name=source_name,
        title=f"[{priority}] {subject}",
        summary=summary,
        url=url,
        published_at=received_dt.replace(microsecond=0).isoformat(),
        fetched_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    ), event


def _decode_mime_header(value: str | None) -> str:
    raw = value or ""
    decoded: List[str] = []
    for text, enc in decode_header(raw):
        if isinstance(text, bytes):
            decoded.append(text.decode(enc or "utf-8", errors="ignore"))
        else:
            decoded.append(str(text))
    return "".join(decoded).strip()


def _parse_mail_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_text_body(message: Message) -> str:
    texts: List[str] = []
    if message.is_multipart():
        parts = message.walk()
    else:
        parts = [message]

    for part in parts:
        content_type = str(part.get_content_type() or "").lower()
        disposition = str(part.get("Content-Disposition", "")).lower()
        if "attachment" in disposition or content_type not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            texts.append(payload.decode(charset, errors="ignore"))
        except Exception:
            texts.append(payload.decode("utf-8", errors="ignore"))

    body = " ".join(texts).strip()
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"\s+", " ", body).strip()
    return body[:3000]


def _classify_mail(
    source: Dict[str, Any],
    *,
    sender: str,
    subject: str,
    body: str,
    action_hit: str = "",
) -> Tuple[str, str]:
    combined = f"{subject}\n{body}".lower()
    sender_lower = sender.lower()
    vip_senders = _string_list(source.get("vip_senders", []))
    urgent_keywords = _string_list(source.get("urgent_keywords", []))
    important_keywords = _string_list(source.get("important_keywords", []))

    if _is_ignored_sender(source, sender_lower):
        return "FYI", "ignored sender"
    if _is_ignored_subject(source, subject.lower()):
        return "FYI", "ignored subject"

    for vip in vip_senders:
        if vip and vip in sender_lower:
            return "Urgent", f"vip sender: {vip}"
    hit = _first_hit(combined, urgent_keywords)
    if hit:
        return "Urgent", f"urgent keyword: {hit}"
    if action_hit:
        return "Urgent", f"near-term action timing: {action_hit}"
    hit = _first_hit(combined, important_keywords)
    if hit:
        return "Important", f"important keyword: {hit}"
    return "FYI", "no critical keyword"


def _string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().lower() for item in value if str(item).strip()]


def _first_hit(text: str, candidates: Iterable[str]) -> str:
    for candidate in candidates:
        if candidate and candidate in text:
            return candidate
    return ""


def _is_ignored_sender(source: Dict[str, Any], sender_lower: str) -> bool:
    ignored_senders = _string_list(source.get("ignored_senders", []))
    return any(item and item in sender_lower for item in ignored_senders)


def _is_ignored_subject(source: Dict[str, Any], subject_lower: str) -> bool:
    ignored_subject_keywords = _string_list(source.get("ignored_subject_keywords", []))
    return any(item and item in subject_lower for item in ignored_subject_keywords)


def _detect_action_timing(source: Dict[str, Any], *, subject: str, body: str) -> str:
    action = _detect_action(source, subject=subject, body=body)
    return str(action.get("label", ""))


def _detect_action(source: Dict[str, Any], *, subject: str, body: str) -> Dict[str, Any]:
    text = f"{subject}\n{body}"
    lower = text.lower()
    action_words = [
        "meeting",
        "appointment",
        "deadline",
        "due",
        "review",
        "call",
        "webinar",
        "interview",
        "会议",
        "开会",
        "截止",
        "到期",
        "面试",
        "电话",
        "评审",
        "审批",
        "提醒",
    ]
    has_action_word = any(word in lower for word in action_words)
    today = datetime.now(timezone.utc).astimezone().date()
    emit_window_days = int(source.get("event_emit_window_days", 0) or 0)

    relative_hit = _relative_date_hit(lower)
    if relative_hit and has_action_word:
        event_date = _relative_date_to_date(relative_hit, today)
        return {
            "label": relative_hit,
            "event_date": event_date.isoformat(),
            "is_due": 0 <= (event_date - today).days <= emit_window_days,
        }

    dates = _extract_candidate_dates(text, today.year)
    for candidate in dates:
        delta = (candidate - today).days
        if delta >= 0 and has_action_word:
            return {
                "label": candidate.isoformat(),
                "event_date": candidate.isoformat(),
                "is_due": delta <= emit_window_days,
            }
    return {}


def _relative_date_hit(text: str) -> str:
    patterns = [
        ("today", "today"),
        ("tomorrow", "tomorrow"),
        ("今天", "今天"),
        ("今日", "今日"),
        ("明天", "明天"),
        ("明日", "明日"),
    ]
    for pattern, label in patterns:
        if pattern in text:
            return label
    return ""


def _relative_date_to_date(label: str, today: date) -> date:
    if label in {"tomorrow", "明天", "明日"}:
        return today + timedelta(days=1)
    return today


def _extract_candidate_dates(text: str, default_year: int) -> List[date]:
    candidates: List[date] = []
    for match in re.finditer(r"\b(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})\b", text):
        candidates.extend(_safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
    for match in re.finditer(r"\b(\d{1,2})[-/.](\d{1,2})\b", text):
        candidates.extend(_safe_date(default_year, int(match.group(1)), int(match.group(2))))
    for match in re.finditer(r"(20\d{2})年(\d{1,2})月(\d{1,2})日?", text):
        candidates.extend(_safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3))))
    for match in re.finditer(r"(\d{1,2})月(\d{1,2})日?", text):
        candidates.extend(_safe_date(default_year, int(match.group(1)), int(match.group(2))))
    return candidates


def _safe_date(year: int, month: int, day: int) -> List[date]:
    try:
        return [date(year, month, day)]
    except ValueError:
        return []


def _mail_lookback_hours(source: Dict[str, Any]) -> int:
    if bool(source.get("_mail_queue_exists", False)):
        return positive_int(source.get("lookback_hours"), 72)
    return positive_int(source.get("initial_backfill_hours"), positive_int(source.get("lookback_hours"), 72))


def _queue_path(source: Dict[str, Any], *, root: Path | None, runtime_config: Dict[str, Any]) -> Path:
    output_dir = Path(str(runtime_config.get("output_dir", "runtime")))
    if root is not None and not output_dir.is_absolute():
        output_dir = root / output_dir
    queue_name = str(source.get("event_queue_file", "mail_event_queue.json")).strip() or "mail_event_queue.json"
    return output_dir / queue_name


def _load_event_queue(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _save_event_queue(path: Path, items: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": utc_now_iso(),
        "count": len(items),
        "items": items,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _merge_event_queue(existing: List[Dict[str, Any]], incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for item in existing + incoming:
        event_id = str(item.get("event_id", "")).strip()
        if event_id:
            by_id[event_id] = item
    return sorted(by_id.values(), key=lambda item: str(item.get("event_date", "")))


def _due_alerts_from_queue(source: Dict[str, Any], queue: List[Dict[str, Any]]) -> Tuple[List[CollectedItem], List[Dict[str, Any]]]:
    today = datetime.now(timezone.utc).astimezone().date()
    emit_window_days = int(source.get("event_emit_window_days", 0) or 0)
    alerts: List[CollectedItem] = []
    remaining: List[Dict[str, Any]] = []
    for event in queue:
        event_date = _parse_date(str(event.get("event_date", "")))
        if event_date is None:
            continue
        delta = (event_date - today).days
        if 0 <= delta <= emit_window_days:
            alerts.append(_event_to_alert(source, event))
            continue
        if delta >= 0:
            remaining.append(event)
    return alerts, remaining


def _event_to_alert(source: Dict[str, Any], event: Dict[str, Any]) -> CollectedItem:
    source_id = str(source.get("id", "mailbox")).strip()
    source_name = str(source.get("name", source_id)).strip()
    title = str(event.get("subject", "(no subject)")).strip() or "(no subject)"
    event_date = str(event.get("event_date", "")).strip()
    sender = str(event.get("sender", "")).strip()
    summary = f"Urgent queued mail event. event_date={event_date}"
    if sender:
        summary += f" | sender={sender}"
    snippet = str(event.get("snippet", "")).strip()
    if snippet:
        summary += f" | {snippet[:240]}"
    return item_from_fields(
        channel="mail_alert",
        source_type="mail_alerts",
        source_id=source_id,
        source_name=source_name,
        title=f"[Urgent] {title}",
        summary=summary,
        url=str(event.get("url", "")) or f"mail:event:{event.get('event_id', '')}",
        published_at=event_date,
        fetched_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    )


def _mail_event(
    source: Dict[str, Any],
    *,
    sender: str,
    subject: str,
    body: str,
    message_id: str,
    received_dt: datetime,
    action: Dict[str, Any],
) -> Dict[str, Any] | None:
    event_date = str(action.get("event_date", "")).strip()
    if not event_date:
        return None
    source_id = str(source.get("id", "mailbox")).strip()
    url = f"mail:{message_id}" if message_id else f"mail:{source_id}:{subject}"
    event_id = make_item_id(source_id, f"{event_date}|{subject}", url)
    return {
        "event_id": event_id,
        "event_date": event_date,
        "source_id": source_id,
        "subject": subject,
        "sender": sender,
        "url": url,
        "received_at": received_dt.replace(microsecond=0).isoformat(),
        "snippet": body[:500],
        "status": "pending",
    }


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _dedup_events(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output: List[Dict[str, Any]] = []
    for item in items:
        key = str(item.get("event_id", "")).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def _dedup_mail_alerts(items: List[CollectedItem]) -> List[CollectedItem]:
    seen = set()
    output: List[CollectedItem] = []
    for item in items:
        key = item.url.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output
