#!/usr/bin/env python3
"""Manage communicate runtime state with JSON authority and Markdown sync."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from runtime_io import atomic_write_json, atomic_write_text, file_lock

INPUT_START = "<!-- INPUT_PAD_START -->"
INPUT_END = "<!-- INPUT_PAD_END -->"
TOC_START = "<!-- REQUEST_INDEX_START -->"
TOC_END = "<!-- REQUEST_INDEX_END -->"
QUEUE_START = "<!-- REQUEST_QUEUE_START -->"
QUEUE_END = "<!-- REQUEST_QUEUE_END -->"
INDEX_START = "<!-- COMPLETION_INDEX_START -->"
INDEX_END = "<!-- COMPLETION_INDEX_END -->"
PLACEHOLDER = "Paste request text here. One request at a time. Include files/paths if relevant."

VALID_STATUS = {"NEW", "ACKED", "IN_PROGRESS", "BLOCKED", "DONE"}
TERMINAL_STATUS = {"BLOCKED", "DONE"}
SYSTEM_BLOCKED = "SYSTEM_BLOCKED"
SYSTEM_RECOVERED = "SYSTEM_RECOVERED"
RUNTIME_VERSION = "1.1.0"
OBJECTIVE_REPORT_PATH = Path("REQ_LOG_NORMALIZATION_REPORT.md")
TRANSITIONS = {
    "NEW": {"ACKED", "BLOCKED"},
    "ACKED": {"IN_PROGRESS", "DONE", "BLOCKED"},
    "IN_PROGRESS": {"DONE", "BLOCKED"},
    "BLOCKED": set(),
    "DONE": set(),
}
INPUT_PAD_KEY = "input_pad"


def _db_connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _init_db(db_path: Path, schema_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = schema_path.read_text(encoding="utf-8")
    with _db_connect(db_path) as conn:
        conn.executescript(schema)
        conn.commit()


def _db_get_request(db_path: Path, request_id: str) -> sqlite3.Row | None:
    with _db_connect(db_path) as conn:
        return conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()


def _extract_title(request_text: str) -> str:
    lines = request_text.splitlines()
    for i, line in enumerate(lines):
        token = line.strip()
        if token in {"TITLE", "TITLE:"}:
            for nxt in lines[i + 1 :]:
                if nxt.strip():
                    return nxt.strip()[:200]
    return (_first_request_line(request_text) or "Untitled request")[:200]


def _ensure_request_in_db_from_json(db_path: Path, schema_path: Path, request_id: str, json_path: Path) -> None:
    if _db_get_request(db_path, request_id) is not None:
        return
    if not json_path.exists():
        raise ValueError(f"Unknown request id: {request_id}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    requests = payload.get("requests", [])
    req = next((r for r in requests if r.get("request_id") == request_id), None)
    if req is None:
        raise ValueError(f"Unknown request id: {request_id}")

    _init_db(db_path, schema_path)
    created_at = req.get("created_at") or _now_iso()
    updated_at = req.get("last_updated_at") or created_at
    title = _extract_title(req.get("request_text", ""))
    objective = req.get("objective") or extract_objective(req.get("request_text", ""))
    status = req.get("status") or "NEW"
    with _db_connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT OR REPLACE INTO requests(id, title, objective, status, created_at, updated_at, archived_flag)
            VALUES(?, ?, ?, ?, ?, ?, 0)
            """,
            (request_id, title, objective, status, created_at, updated_at),
        )
        raw_log = (req.get("execution_log") or "").strip()
        if raw_log:
            for line in raw_log.splitlines():
                if line.strip():
                    conn.execute(
                        "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                        (request_id, line.strip(), _now_iso()),
                    )
        _db_upsert_communicate_req(
            conn,
            req_id=request_id,
            title=title,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            source="communicate>",
            structured_payload=req.get("request_text", ""),
        )
        conn.commit()


def _next_id_from_db(db_path: Path) -> str:
    base = dt.datetime.now().strftime("REQ-%Y%m%d-%H%M%S")
    with _db_connect(db_path) as conn:
        rows = conn.execute("SELECT id FROM requests WHERE id LIKE ?", (f"{base}%",)).fetchall()
    existing = {r["id"] for r in rows}
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def _transition_status_value(current: str, target_status: str) -> str:
    if current in TERMINAL_STATUS:
        raise ValueError(f"Terminal state is immutable: {current}")
    if target_status not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid status transition: {current} -> {target_status}")
    return target_status


def _db_upsert_communicate_req(
    conn: sqlite3.Connection,
    req_id: str,
    title: str,
    status: str,
    created_at: str,
    updated_at: str,
    source: str,
    structured_payload: str,
) -> None:
    conn.execute(
        """
        INSERT INTO communicate_reqs(req_id, title, status, created_at, updated_at, source, structured_payload)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(req_id) DO UPDATE SET
          title=excluded.title,
          status=excluded.status,
          updated_at=excluded.updated_at,
          source=excluded.source,
          structured_payload=excluded.structured_payload
        """,
        (req_id, title, status, created_at, updated_at, source, structured_payload),
    )


def _db_get_input_text(db_path: Path) -> str:
    with _db_connect(db_path) as conn:
        row = conn.execute(
            "SELECT text_value FROM runtime_input_pad WHERE pad_key = ?",
            (INPUT_PAD_KEY,),
        ).fetchone()
    if row is None:
        return ""
    return str(row["text_value"] or "").strip()


def _db_set_input_text(db_path: Path, text: str) -> None:
    ts = _now_iso()
    with _db_connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO runtime_input_pad(pad_key, text_value, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(pad_key) DO UPDATE SET
              text_value=excluded.text_value,
              updated_at=excluded.updated_at
            """,
            (INPUT_PAD_KEY, text.strip(), ts),
        )
        conn.commit()


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _safe_parse_iso(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts)


def _monotonic_iso(previous: Optional[str]) -> str:
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    if previous:
        prev = _safe_parse_iso(previous)
        if now <= prev:
            now = prev + dt.timedelta(seconds=1)
    return now.isoformat()


def _section(text: str, start: str, end: str) -> str:
    pattern = re.compile(re.escape(start) + r"\n?(.*?)\n?" + re.escape(end), re.DOTALL)
    match = pattern.search(text)
    if not match:
        raise ValueError(
            f"Missing section markers: {start} .. {end}. "
            f"Repair: restore required markers in communicate.md before rerun."
        )
    return match.group(1)


def _replace_section(text: str, start: str, end: str, content: str) -> str:
    pattern = re.compile(re.escape(start) + r"\n?(.*?)\n?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{content.rstrip()}\n{end}"
    # Use callable replacement so backslashes in content are treated literally.
    new_text, count = pattern.subn(lambda _m: replacement, text, count=1)
    if count != 1:
        raise ValueError(
            f"Could not replace section: {start} .. {end}. "
            f"Repair: restore required markers in communicate.md before rerun."
        )
    return new_text


def _load_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def _file_sha256(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _extract_field(block_text: str, name: str) -> str:
    pattern = re.compile(
        rf"### {re.escape(name)}\n(.*?)(?=\n### [A-Za-z_]+\n|\n<!-- REQUEST:|\Z)",
        re.DOTALL,
    )
    match = pattern.search(block_text)
    return match.group(1).strip() if match else ""


def parse_blocks_from_markdown(queue_section: str) -> List[Dict[str, str]]:
    pattern = re.compile(
        r"<!-- REQUEST:([^\s]+) START -->(.*?)<!-- REQUEST:\1 END -->",
        re.DOTALL,
    )
    blocks: List[Dict[str, str]] = []
    for match in pattern.finditer(queue_section):
        request_id = match.group(1).strip()
        raw = match.group(2)
        anchor = re.search(r'<a id="([^"]+)"></a>', raw)
        if anchor and anchor.group(1) != request_id:
            raise ValueError(
                f"Anchor mismatch in {request_id}: found {anchor.group(1)}. "
                "Repair: align REQ anchor id with request id."
            )
        status = _extract_field(raw, "status")
        if status not in VALID_STATUS:
            status = "NEW"
        blocks.append(
            {
                "request_id": request_id,
                "status": status,
                "author": _extract_field(raw, "author") or "USER",
                "created_at": _extract_field(raw, "created_at") or _now_iso(),
                "last_updated_at": _extract_field(raw, "last_updated_at") or _now_iso(),
                "request_text": _extract_field(raw, "request_text"),
                "objective": _extract_field(raw, "objective"),
                "codex_ack_plan": _extract_field(raw, "codex_ack_plan"),
                "execution_log": _extract_field(raw, "execution_log"),
                "outputs": _extract_field(raw, "outputs"),
                "evidence": _extract_field(raw, "evidence"),
                "next_steps_if_blocked": _extract_field(raw, "next_steps_if_blocked"),
            }
        )
    return blocks


def _render_block(block: Dict[str, str]) -> str:
    return (
        f"<!-- REQUEST:{block['request_id']} START -->\n"
        f"<a id=\"{block['request_id']}\"></a>\n"
        f"## REQUEST {block['request_id']}\n"
        f"### status\n{block['status']}\n"
        f"### author\n{block['author']}\n"
        f"### created_at\n{block['created_at']}\n"
        f"### last_updated_at\n{block['last_updated_at']}\n"
        f"### request_text\n{block['request_text']}\n"
        f"### objective\n{block.get('objective', '')}\n"
        f"### codex_ack_plan\n{block['codex_ack_plan']}\n"
        f"### execution_log\n{block['execution_log']}\n"
        f"### outputs\n{block['outputs']}\n"
        f"### evidence\n{block['evidence']}\n"
        f"### next_steps_if_blocked\n{block['next_steps_if_blocked']}\n"
        f"<!-- REQUEST:{block['request_id']} END -->"
    )


def _request_sort_key(req: Dict[str, str]) -> Tuple[dt.datetime, str]:
    created_at = req.get("created_at") or ""
    return (_safe_parse_iso(created_at), req.get("request_id", ""))


def _render_ordered_requests(requests: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # Render newest-first in Markdown while preserving canonical JSON order.
    return sorted(requests, key=_request_sort_key, reverse=True)


def _render_queue(requests: List[Dict[str, str]]) -> str:
    header = "<!-- New request blocks are appended here by scripts/communicate_scan.py -->"
    body = "\n\n".join(_render_block(r) for r in _render_ordered_requests(requests))
    return f"{header}\n\n{body}".rstrip()


def _first_request_line(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def _is_all_caps_header(line: str) -> bool:
    token = line.strip().rstrip(":")
    if not token:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z0-9 _-]*", token))


def _is_objective_stop_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if _is_all_caps_header(stripped):
        return True
    if re.match(r"^[A-Z _-]+:$", stripped):
        return True
    return False


def _sentence_count(text: str) -> int:
    parts = [p for p in re.split(r"[.!?]+(?:\s+|$)", text.strip()) if p.strip()]
    return len(parts)


def validate_objective(text: str) -> bool:
    content = text.strip()
    if not content:
        return False
    if len(content) > 4000:
        return False
    upper = content.upper()
    if "SECTION" in upper or "REQUIRED ACTIONS" in upper:
        return False
    if "```" in content:
        return False
    return True


def extract_objective(request_text: str) -> str:
    lines = request_text.splitlines()
    objective_idx = None
    for i, line in enumerate(lines):
        token = line.strip()
        if token == "OBJECTIVE" or token == "OBJECTIVE:":
            objective_idx = i
            break
    if objective_idx is None:
        raise ValueError("OBJECTIVE section missing — REQ entry not recorded.")

    captured: List[str] = []
    for line in lines[objective_idx + 1 :]:
        if _is_objective_stop_line(line):
            break
        captured.append(line.strip())
    objective = " ".join(part for part in captured if part).strip()
    if not validate_objective(objective):
        raise ValueError("OBJECTIVE field invalid — contains non-objective content.")
    return objective


def _sanitize_objective_fallback(text: str) -> str:
    cleaned: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            break
        if _is_all_caps_header(line) or re.match(r"^[A-Z _-]+:$", line) or line.startswith("#"):
            continue
        cleaned.append(line)
    candidate = " ".join(cleaned).strip()
    sentences = re.split(r"(?<=[.!?])\s+", candidate)
    candidate = " ".join(sentences[:3]).strip()
    return candidate[:500].strip()


def _normalize_objectives(state: Dict, report_path: Path) -> int:
    fixed = 0
    examples: List[Tuple[str, str, str]] = []
    for req in state.get("requests", []):
        before = (req.get("objective") or "").strip()
        if validate_objective(before):
            continue

        source = (req.get("request_text") or "").strip()
        after = ""
        if source:
            try:
                after = extract_objective(source)
            except ValueError:
                after = _sanitize_objective_fallback(before or source)
        else:
            after = _sanitize_objective_fallback(before)
        if not validate_objective(after):
            continue

        req["objective"] = after
        fixed += 1
        examples.append((req.get("request_id", "UNKNOWN"), before, after))

    lines = [
        "# REQ_LOG_NORMALIZATION_REPORT",
        "",
        f"- Generated at: {_now_iso()}",
        f"- Malformed entries fixed: {fixed}",
        "",
    ]
    if examples:
        lines.append("## Example Before/After")
        for rid, before, after in examples[:5]:
            lines.append(f"- {rid}")
            lines.append(f"  - before: {(before or '(empty)')[:180]}")
            lines.append(f"  - after: {after[:180]}")
    else:
        lines.append("No malformed entries required normalization.")
    atomic_write_text(report_path, "\n".join(lines) + "\n")
    return fixed


def _render_request_index(requests: List[Dict[str, str]]) -> str:
    lines = ["<!-- Auto-generated by scripts/communicate_scan.py -->"]
    for req in _render_ordered_requests(requests):
        summary = (req.get("objective") or "").strip() or _first_request_line(req.get("request_text", ""))
        if len(summary) > 120:
            summary = summary[:117].rstrip() + "..."
        lines.append(f"- [{req['request_id']}](#{req['request_id']}) — {req['status']} — {summary}")
    return "\n".join(lines)


def _render_index(requests: List[Dict[str, str]]) -> str:
    lines = ["<!-- Auto-generated by scripts/communicate_scan.py -->"]
    for req in _render_ordered_requests(requests):
        if req["status"] in TERMINAL_STATUS:
            lines.append(f"- {req['request_id']}: {req['status']}")
    return "\n".join(lines)


def _validate_state(state: Dict) -> None:
    if not isinstance(state, dict):
        raise ValueError("Invalid JSON state root. Repair: restore communicate.json object payload.")
    if "requests" not in state or not isinstance(state["requests"], list):
        raise ValueError("Invalid JSON schema. Repair: add list field 'requests' to communicate.json.")

    seen = set()
    for req in state["requests"]:
        rid = req.get("request_id", "")
        if not rid:
            raise ValueError("Invalid request without request_id. Repair: add stable request_id.")
        if rid in seen:
            raise ValueError(f"Duplicate request_id '{rid}'. Repair: deduplicate request ids.")
        seen.add(rid)

        status = req.get("status")
        if status not in VALID_STATUS:
            raise ValueError(f"Invalid status '{status}' in {rid}. Repair: set valid status.")

        created = req.get("created_at")
        updated = req.get("last_updated_at")
        if not created or not updated:
            raise ValueError(f"Missing timestamps in {rid}. Repair: set created_at and last_updated_at.")
        if _safe_parse_iso(updated) < _safe_parse_iso(created):
            raise ValueError(f"Non-monotonic timestamps in {rid}. Repair: ensure last_updated_at >= created_at.")


def _bootstrap_state_from_markdown(md_path: Path) -> Dict:
    text = _load_text(md_path)
    queue = _section(text, QUEUE_START, QUEUE_END)
    requests = parse_blocks_from_markdown(queue)
    state = {
        "schema_version": 1,
        "canonical_store": "communicate.json",
        "requests": requests,
    }
    _validate_state(state)
    return state


def _load_state(json_path: Path, md_path: Path) -> Dict:
    if json_path.exists():
        try:
            state = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"JSON parse failure in {json_path}: {exc}. "
                "Repair: fix JSON syntax before rerun."
            ) from exc
        _validate_state(state)
        fixed = _normalize_objectives(state, OBJECTIVE_REPORT_PATH)
        if fixed:
            atomic_write_json(json_path, state)
        return state

    state = _bootstrap_state_from_markdown(md_path)
    _normalize_objectives(state, OBJECTIVE_REPORT_PATH)
    atomic_write_json(json_path, state)
    return state


def _default_json_path(md_path: Path) -> Path:
    return md_path.with_suffix(".json")


def _default_failure_log_path(json_path: Path) -> Path:
    return json_path.with_name("failure_log.json")


def _load_failure_log(path: Path) -> Dict:
    if not path.exists():
        return {"schema_version": 1, "events": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failure log parse error in {path}: {exc}. "
            "Repair: fix failure_log.json syntax before rerun."
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError(
            f"Failure log schema invalid in {path}. "
            "Repair: restore object with list field 'events'."
        )
    return payload


def _append_failure_event(path: Path, event: Dict) -> None:
    payload = _load_failure_log(path)
    payload["events"].append(event)
    atomic_write_json(path, payload)


def _active_system_blocks(payload: Dict) -> List[Dict]:
    events = payload.get("events", [])
    recovered_ids = {
        e.get("blocked_event_id")
        for e in events
        if e.get("event_type") == SYSTEM_RECOVERED and e.get("blocked_event_id")
    }
    active = [
        e
        for e in events
        if e.get("event_type") == SYSTEM_BLOCKED
        and e.get("event_id") not in recovered_ids
    ]
    return active


def _is_structural_error(exc: Exception) -> bool:
    msg = str(exc)
    patterns = (
        "JSON parse failure",
        "Invalid JSON",
        "Missing section markers",
        "Anchor mismatch",
        "Failure log parse error",
        "Failure log schema invalid",
    )
    return any(p in msg for p in patterns)


def _classify_structural_failure(exc: Exception, json_path: Path, md_path: Path) -> Tuple[str, Path]:
    msg = str(exc)
    if "Missing section markers" in msg:
        return "STRUCTURAL_MARKDOWN_FAILURE", md_path
    return "STRUCTURAL_JSON_FAILURE", json_path


def _record_system_block(
    failure_log_path: Path,
    source_path: Path,
    failure_scope: str,
    error_type: str,
    error_details: str,
    repair_instructions: str,
) -> Dict:
    payload = _load_failure_log(failure_log_path)
    source_hash = _file_sha256(source_path)
    source_file = str(source_path)
    for event in _active_system_blocks(payload):
        if (
            event.get("source_file") == source_file
            and event.get("source_hash") == source_hash
            and event.get("failure_scope") == failure_scope
            and event.get("error_type") == error_type
        ):
            return event

    event_id = f"SYS-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(payload['events']) + 1}"
    event = {
        "event_id": event_id,
        "failure_scope": failure_scope,
        "event_type": SYSTEM_BLOCKED,
        "timestamp": _now_iso(),
        "error_type": error_type,
        "error_details": error_details,
        "repair_instructions": repair_instructions,
        "source_file": source_file,
        "source_hash": source_hash,
        # Backward-compatible aliases retained for existing tooling.
        "file_path": source_file,
        "file_hash": source_hash,
        "runtime_version": RUNTIME_VERSION,
    }
    _append_failure_event(failure_log_path, event)
    return event


def _maybe_clear_system_block(failure_log_path: Path, json_path: Path, md_path: Path) -> None:
    payload = _load_failure_log(failure_log_path)
    active = _active_system_blocks(payload)
    if not active:
        return

    latest = active[-1]
    source_path = Path(latest.get("source_file") or latest.get("file_path") or str(json_path))
    current_hash = _file_sha256(source_path)
    previous_hash = latest.get("source_hash") or latest.get("file_hash")
    if current_hash == previous_hash:
        raise ValueError(
            f"{SYSTEM_BLOCKED}: unresolved structural failure for {source_path}. "
            f"Repair required before execution. Failure event: {latest.get('event_id')}"
        )

    _load_state(json_path, md_path)
    recovery = {
        "event_id": f"SYSREC-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(payload['events']) + 1}",
        "event_type": SYSTEM_RECOVERED,
        "timestamp": _now_iso(),
        "blocked_event_id": latest.get("event_id"),
        "source_file": str(source_path),
        "source_hash": current_hash,
        "file_path": str(source_path),
        "file_hash": current_hash,
        "runtime_version": RUNTIME_VERSION,
        "notes": "Manual repair detected and canonical state validated.",
    }
    _append_failure_event(failure_log_path, recovery)


def system_status(md_path: Path, json_path: Path, failure_log_path: Path) -> int:
    try:
        _maybe_clear_system_block(failure_log_path, json_path, md_path)
    except Exception as exc:
        if SYSTEM_BLOCKED in str(exc):
            print(str(exc), file=sys.stderr)
            return 2
        raise
    print("SYSTEM_OK")
    return 0


def _next_id(requests: List[Dict[str, str]]) -> str:
    base = dt.datetime.now().strftime("REQ-%Y%m%d-%H%M%S")
    existing = {r["request_id"] for r in requests}
    if base not in existing:
        return base
    i = 2
    while f"{base}-{i}" in existing:
        i += 1
    return f"{base}-{i}"


def _find_request(state: Dict, request_id: str) -> Dict[str, str]:
    for req in state["requests"]:
        if req["request_id"] == request_id:
            return req
    raise ValueError(f"Unknown request id: {request_id}")


def _transition(req: Dict[str, str], target_status: str) -> None:
    current = req["status"]
    if current in TERMINAL_STATUS:
        raise ValueError(f"Terminal state is immutable: {current}")
    if target_status not in TRANSITIONS.get(current, set()):
        raise ValueError(f"Invalid status transition: {current} -> {target_status}")
    req["status"] = target_status
    req["last_updated_at"] = _monotonic_iso(req.get("last_updated_at"))


def _sync_markdown(md_path: Path, requests: List[Dict[str, str]], input_pad_content: Optional[str] = None) -> None:
    text = _load_text(md_path)
    _section(text, TOC_START, TOC_END)
    _section(text, QUEUE_START, QUEUE_END)
    _section(text, INDEX_START, INDEX_END)
    if input_pad_content is not None:
        _section(text, INPUT_START, INPUT_END)
        text = _replace_section(text, INPUT_START, INPUT_END, input_pad_content)
    text = _replace_section(text, TOC_START, TOC_END, _render_request_index(requests))
    text = _replace_section(text, QUEUE_START, QUEUE_END, _render_queue(requests))
    text = _replace_section(text, INDEX_START, INDEX_END, _render_index(requests))
    atomic_write_text(md_path, text)


def consume(md_path: Path, json_path: Path, db_path: Path, schema_path: Path, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        _init_db(db_path, schema_path)
        input_text = _db_get_input_text(db_path)
        if not input_text or input_text == PLACEHOLDER:
            print("No new INPUT PAD content. Nothing to do.")
            return 0
        objective = extract_objective(input_text)
        req_id = _next_id_from_db(db_path)
        created = _now_iso()
        title = _extract_title(input_text)
        with _db_connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO requests(id, title, objective, status, created_at, updated_at, archived_flag)
                VALUES(?, ?, ?, ?, ?, ?, 0)
                """,
                (req_id, title, objective, "NEW", created, created),
            )
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (req_id, f"REQUEST_TEXT::{input_text}", created),
            )
            _db_upsert_communicate_req(
                conn,
                req_id=req_id,
                title=title,
                status="NEW",
                created_at=created,
                updated_at=created,
                source="communicate>",
                structured_payload=input_text,
            )
            conn.commit()
        _db_set_input_text(db_path, PLACEHOLDER)
        print(req_id)
        return 0


def ack(md_path: Path, json_path: Path, db_path: Path, schema_path: Path, request_id: str, plan: str, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        _init_db(db_path, schema_path)
        _ensure_request_in_db_from_json(db_path, schema_path, request_id, json_path)
        row = _db_get_request(db_path, request_id)
        if row is None:
            raise ValueError(f"Unknown request id: {request_id}")
        next_status = _transition_status_value(str(row["status"]), "ACKED")
        ts = _monotonic_iso(str(row["updated_at"]))
        with _db_connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE requests SET status = ?, updated_at = ? WHERE id = ?", (next_status, ts, request_id))
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, f"ACK_PLAN::{plan}", ts),
            )
            title = str(row["title"])
            payload_row = conn.execute(
                "SELECT structured_payload, created_at FROM communicate_reqs WHERE req_id = ?",
                (request_id,),
            ).fetchone()
            structured_payload = str(payload_row["structured_payload"]) if payload_row else ""
            created_at = str(payload_row["created_at"]) if payload_row else str(row["created_at"])
            _db_upsert_communicate_req(
                conn,
                req_id=request_id,
                title=title,
                status=next_status,
                created_at=created_at,
                updated_at=ts,
                source="communicate>",
                structured_payload=structured_payload,
            )
            conn.commit()
        return 0


def log(md_path: Path, json_path: Path, db_path: Path, schema_path: Path, request_id: str, message: str, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        _init_db(db_path, schema_path)
        _ensure_request_in_db_from_json(db_path, schema_path, request_id, json_path)
        row = _db_get_request(db_path, request_id)
        if row is None:
            raise ValueError(f"Unknown request id: {request_id}")
        current = str(row["status"])
        if current == "ACKED":
            next_status = "IN_PROGRESS"
        elif current == "IN_PROGRESS":
            next_status = "IN_PROGRESS"
        else:
            raise ValueError(f"Cannot append log while status is {current}")
        ts = _monotonic_iso(str(row["updated_at"]))
        with _db_connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE requests SET status = ?, updated_at = ? WHERE id = ?", (next_status, ts, request_id))
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, message, ts),
            )
            payload_row = conn.execute(
                "SELECT structured_payload, created_at FROM communicate_reqs WHERE req_id = ?",
                (request_id,),
            ).fetchone()
            structured_payload = str(payload_row["structured_payload"]) if payload_row else ""
            created_at = str(payload_row["created_at"]) if payload_row else str(row["created_at"])
            _db_upsert_communicate_req(
                conn,
                req_id=request_id,
                title=str(row["title"]),
                status=next_status,
                created_at=created_at,
                updated_at=ts,
                source="communicate>",
                structured_payload=structured_payload,
            )
            conn.commit()
        return 0


def complete(
    md_path: Path,
    json_path: Path,
    db_path: Path,
    schema_path: Path,
    request_id: str,
    result: str,
    evidence: str,
    lock_timeout: int,
) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        _init_db(db_path, schema_path)
        _ensure_request_in_db_from_json(db_path, schema_path, request_id, json_path)
        row = _db_get_request(db_path, request_id)
        if row is None:
            raise ValueError(f"Unknown request id: {request_id}")
        current = str(row["status"])
        if current not in {"ACKED", "IN_PROGRESS"}:
            raise ValueError(f"Cannot complete while status is {current}")
        ts = _monotonic_iso(str(row["updated_at"]))
        with _db_connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO verification_blocks(request_id, objectives_addressed, quality_checks, risks, final_status)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                  objectives_addressed=excluded.objectives_addressed,
                  quality_checks=excluded.quality_checks,
                  risks=excluded.risks,
                  final_status=excluded.final_status
                """,
                (request_id, result.strip(), evidence.strip(), "N/A", "DONE"),
            )
            conn.execute("UPDATE requests SET status = ?, updated_at = ? WHERE id = ?", ("DONE", ts, request_id))
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, f"RESULT::{result}", ts),
            )
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, f"EVIDENCE::{evidence}", ts),
            )
            payload_row = conn.execute(
                "SELECT structured_payload, created_at FROM communicate_reqs WHERE req_id = ?",
                (request_id,),
            ).fetchone()
            structured_payload = str(payload_row["structured_payload"]) if payload_row else ""
            created_at = str(payload_row["created_at"]) if payload_row else str(row["created_at"])
            _db_upsert_communicate_req(
                conn,
                req_id=request_id,
                title=str(row["title"]),
                status="DONE",
                created_at=created_at,
                updated_at=ts,
                source="communicate>",
                structured_payload=structured_payload,
            )
            conn.commit()
        return 0


def block(
    md_path: Path,
    json_path: Path,
    db_path: Path,
    schema_path: Path,
    request_id: str,
    reason: str,
    next_steps: str,
    lock_timeout: int,
) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        _init_db(db_path, schema_path)
        _ensure_request_in_db_from_json(db_path, schema_path, request_id, json_path)
        row = _db_get_request(db_path, request_id)
        if row is None:
            raise ValueError(f"Unknown request id: {request_id}")
        current = str(row["status"])
        if current in TERMINAL_STATUS:
            raise ValueError(f"Terminal state is immutable: {current}")
        next_status = _transition_status_value(current, "BLOCKED")
        ts = _monotonic_iso(str(row["updated_at"]))
        with _db_connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("UPDATE requests SET status = ?, updated_at = ? WHERE id = ?", (next_status, ts, request_id))
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, f"BLOCKED::{reason}", ts),
            )
            conn.execute(
                "INSERT INTO logs(request_id, log_entry, timestamp) VALUES(?, ?, ?)",
                (request_id, f"NEXT_STEPS::{next_steps}", ts),
            )
            payload_row = conn.execute(
                "SELECT structured_payload, created_at FROM communicate_reqs WHERE req_id = ?",
                (request_id,),
            ).fetchone()
            structured_payload = str(payload_row["structured_payload"]) if payload_row else ""
            created_at = str(payload_row["created_at"]) if payload_row else str(row["created_at"])
            _db_upsert_communicate_req(
                conn,
                req_id=request_id,
                title=str(row["title"]),
                status=next_status,
                created_at=created_at,
                updated_at=ts,
                source="communicate>",
                structured_payload=structured_payload,
            )
            conn.commit()
        return 0


def set_input(
    md_path: Path,
    json_path: Path,
    db_path: Path,
    schema_path: Path,
    text: str,
    lock_timeout: int,
) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        del md_path
        _init_db(db_path, schema_path)
        _db_set_input_text(db_path, text.strip())
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="commscribe/communicate.md", help="Path to communicate.md")
    parser.add_argument("--json", default=None, help="Path to canonical communicate.json")
    parser.add_argument("--db", default="commscribe/db/communicate.db", help="Path to SQLite communicate.db")
    parser.add_argument("--schema", default="commscribe/db/schema.sql", help="Path to SQLite schema.sql")
    parser.add_argument("--failure-log", default=None, help="Path to append-only failure_log.json")
    parser.add_argument("--lock-timeout", type=int, default=5, help="Lock acquisition timeout in seconds")

    sub = parser.add_subparsers(dest="cmd", required=False)
    sub.add_parser("consume")
    sub.add_parser("system-status")

    p_ack = sub.add_parser("ack")
    p_ack.add_argument("--id", required=True)
    p_ack.add_argument("--plan", required=True)

    p_log = sub.add_parser("log")
    p_log.add_argument("--id", required=True)
    p_log.add_argument("--message", required=True)

    p_done = sub.add_parser("complete")
    p_done.add_argument("--id", required=True)
    p_done.add_argument("--result", required=True)
    p_done.add_argument("--evidence", required=True)

    p_block = sub.add_parser("block")
    p_block.add_argument("--id", required=True)
    p_block.add_argument("--reason", required=True)
    p_block.add_argument("--next-steps", required=True)

    p_set_input = sub.add_parser("set-input")
    p_set_input.add_argument("--text", required=True)

    p_sql_init = sub.add_parser("sqlite-init")
    p_sql_init.add_argument("--db", default=None)
    p_sql_init.add_argument("--schema", default=None)

    p_sql_status = sub.add_parser("sqlite-status")
    p_sql_status.add_argument("--id")
    p_sql_status.add_argument("--db", default=None)
    p_sql_status.add_argument("--schema", default=None)

    p_sql_export = sub.add_parser("sqlite-export-md")
    p_sql_export.add_argument("--output", required=True)
    p_sql_export.add_argument("--db", default=None)
    p_sql_export.add_argument("--schema", default=None)

    p_sql_migrate = sub.add_parser("sqlite-migrate-from-md")
    p_sql_migrate.add_argument("--db", default=None)
    p_sql_migrate.add_argument("--schema", default=None)
    p_sql_migrate.add_argument("--report", default="commscribe/docs/SQLITE_ENGINE_MIGRATION_REPORT.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    md_path = Path(args.file)
    json_path = Path(args.json) if args.json else _default_json_path(md_path)
    db_path = Path(args.db)
    schema_path = Path(args.schema)
    failure_log_path = Path(args.failure_log) if args.failure_log else _default_failure_log_path(json_path)
    cmd = args.cmd or "consume"

    try:
        if cmd in {"sqlite-init", "sqlite-status", "sqlite-export-md", "sqlite-migrate-from-md"}:
            root = Path(__file__).resolve().parents[1]
            cli_script = root / "cli" / "communicate.py"
            mig_script = root / "db" / "migrate_from_md.py"
            db_path = getattr(args, "db", None) or "commscribe/db/communicate.db"
            schema_path = getattr(args, "schema", None) or "commscribe/db/schema.sql"
            base = [sys.executable, str(cli_script), "--db", str(db_path), "--schema", str(schema_path)]
            if cmd == "sqlite-init":
                subprocess.run(base + ["status"], check=False, capture_output=True, text=True)
                print(str(db_path))
                return 0
            if cmd == "sqlite-status":
                c = base + ["status"]
                if args.id:
                    c += ["--id", args.id]
                out = subprocess.run(c, check=True, capture_output=True, text=True)
                print(out.stdout.strip())
                return 0
            if cmd == "sqlite-export-md":
                out = subprocess.run(
                    base + ["export-md", "--output", args.output],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print(out.stdout.strip())
                return 0
            if cmd == "sqlite-migrate-from-md":
                out = subprocess.run(
                    [
                        sys.executable,
                        str(mig_script),
                        "--md",
                        str(md_path),
                        "--json",
                        str(json_path),
                        "--db",
                        str(db_path),
                        "--schema",
                        str(schema_path),
                        "--report",
                        str(args.report),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                print(out.stdout.strip())
                return 0

        if cmd == "system-status":
            return system_status(md_path, json_path, failure_log_path)
        _maybe_clear_system_block(failure_log_path, json_path, md_path)
        if cmd == "consume":
            return consume(md_path, json_path, db_path, schema_path, args.lock_timeout)
        if cmd == "ack":
            return ack(md_path, json_path, db_path, schema_path, args.id, args.plan, args.lock_timeout)
        if cmd == "log":
            return log(md_path, json_path, db_path, schema_path, args.id, args.message, args.lock_timeout)
        if cmd == "complete":
            return complete(md_path, json_path, db_path, schema_path, args.id, args.result, args.evidence, args.lock_timeout)
        if cmd == "block":
            return block(md_path, json_path, db_path, schema_path, args.id, args.reason, args.next_steps, args.lock_timeout)
        if cmd == "set-input":
            return set_input(md_path, json_path, db_path, schema_path, args.text, args.lock_timeout)
    except Exception as exc:
        if _is_structural_error(exc):
            failure_scope, source_path = _classify_structural_failure(exc, json_path, md_path)
            block_event = _record_system_block(
                failure_log_path=failure_log_path,
                source_path=source_path,
                failure_scope=failure_scope,
                error_type=type(exc).__name__,
                error_details=str(exc),
                repair_instructions="Fix canonical/failure-log structure, then rerun command.",
            )
            print(
                f"ERROR: {SYSTEM_BLOCKED} persisted in {failure_log_path} "
                f"(event_id={block_event.get('event_id')}). {exc}",
                file=sys.stderr,
            )
            return 1
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
