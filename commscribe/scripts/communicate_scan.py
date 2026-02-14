#!/usr/bin/env python3
"""Manage communicate runtime state with JSON authority and Markdown sync."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
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
TRANSITIONS = {
    "NEW": {"ACKED", "BLOCKED"},
    "ACKED": {"IN_PROGRESS", "DONE", "BLOCKED"},
    "IN_PROGRESS": {"DONE", "BLOCKED"},
    "BLOCKED": set(),
    "DONE": set(),
}


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


def _render_request_index(requests: List[Dict[str, str]]) -> str:
    lines = ["<!-- Auto-generated by scripts/communicate_scan.py -->"]
    for req in _render_ordered_requests(requests):
        summary = _first_request_line(req.get("request_text", ""))
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
        return state

    state = _bootstrap_state_from_markdown(md_path)
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


def consume(md_path: Path, json_path: Path, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        md_text = _load_text(md_path)
        # Preflight canonical integrity even for empty INPUT PAD so blocked/system failures
        # are always surfaced and never masked by a no-op return.
        state = _load_state(json_path, md_path)
        input_text = _section(md_text, INPUT_START, INPUT_END).strip()
        if not input_text or input_text == PLACEHOLDER:
            print("No new INPUT PAD content. Nothing to do.")
            return 0

        req_id = _next_id(state["requests"])
        created = _now_iso()
        state["requests"].append(
            {
                "request_id": req_id,
                "status": "NEW",
                "author": "USER",
                "created_at": created,
                "last_updated_at": created,
                "request_text": input_text,
                "codex_ack_plan": "",
                "execution_log": "",
                "outputs": "",
                "evidence": "",
                "next_steps_if_blocked": "",
            }
        )
        _validate_state(state)
        atomic_write_json(json_path, state)
        _sync_markdown(md_path, state["requests"], input_pad_content=PLACEHOLDER)
        print(req_id)
        return 0


def ack(md_path: Path, json_path: Path, request_id: str, plan: str, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        state = _load_state(json_path, md_path)
        req = _find_request(state, request_id)
        _transition(req, "ACKED")
        req["codex_ack_plan"] = (req["codex_ack_plan"] + "\n" + plan).strip()
        _validate_state(state)
        atomic_write_json(json_path, state)
        _sync_markdown(md_path, state["requests"])
        return 0


def log(md_path: Path, json_path: Path, request_id: str, message: str, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        state = _load_state(json_path, md_path)
        req = _find_request(state, request_id)
        if req["status"] == "ACKED":
            _transition(req, "IN_PROGRESS")
        elif req["status"] == "IN_PROGRESS":
            req["last_updated_at"] = _monotonic_iso(req.get("last_updated_at"))
        else:
            raise ValueError(f"Cannot append log while status is {req['status']}")
        entry = f"- {_now_iso()} {message}"
        req["execution_log"] = (req["execution_log"] + "\n" + entry).strip()
        _validate_state(state)
        atomic_write_json(json_path, state)
        _sync_markdown(md_path, state["requests"])
        return 0


def complete(
    md_path: Path,
    json_path: Path,
    request_id: str,
    result: str,
    evidence: str,
    lock_timeout: int,
) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        state = _load_state(json_path, md_path)
        req = _find_request(state, request_id)
        if req["status"] in {"ACKED", "IN_PROGRESS"}:
            _transition(req, "DONE")
        else:
            raise ValueError(f"Cannot complete while status is {req['status']}")
        req["outputs"] = (req["outputs"] + "\n" + result).strip()
        req["evidence"] = (req["evidence"] + "\n" + evidence).strip()
        _validate_state(state)
        atomic_write_json(json_path, state)
        _sync_markdown(md_path, state["requests"])
        return 0


def block(
    md_path: Path,
    json_path: Path,
    request_id: str,
    reason: str,
    next_steps: str,
    lock_timeout: int,
) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        state = _load_state(json_path, md_path)
        req = _find_request(state, request_id)
        if req["status"] in TERMINAL_STATUS:
            raise ValueError(f"Terminal state is immutable: {req['status']}")
        _transition(req, "BLOCKED")
        req["outputs"] = (req["outputs"] + "\nBLOCKED: " + reason).strip()
        req["next_steps_if_blocked"] = (req["next_steps_if_blocked"] + "\n" + next_steps).strip()
        _validate_state(state)
        atomic_write_json(json_path, state)
        _sync_markdown(md_path, state["requests"])
        return 0


def set_input(md_path: Path, json_path: Path, text: str, lock_timeout: int) -> int:
    with file_lock(json_path.with_suffix(json_path.suffix + ".lock"), timeout_seconds=lock_timeout):
        full = _load_text(md_path)
        _section(full, INPUT_START, INPUT_END)
        full = _replace_section(full, INPUT_START, INPUT_END, text.strip())
        atomic_write_text(md_path, full)
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="commscribe/communicate.md", help="Path to communicate.md")
    parser.add_argument("--json", default=None, help="Path to canonical communicate.json")
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    md_path = Path(args.file)
    json_path = Path(args.json) if args.json else _default_json_path(md_path)
    failure_log_path = Path(args.failure_log) if args.failure_log else _default_failure_log_path(json_path)
    cmd = args.cmd or "consume"

    try:
        if cmd == "system-status":
            return system_status(md_path, json_path, failure_log_path)
        _maybe_clear_system_block(failure_log_path, json_path, md_path)
        if cmd == "consume":
            return consume(md_path, json_path, args.lock_timeout)
        if cmd == "ack":
            return ack(md_path, json_path, args.id, args.plan, args.lock_timeout)
        if cmd == "log":
            return log(md_path, json_path, args.id, args.message, args.lock_timeout)
        if cmd == "complete":
            return complete(md_path, json_path, args.id, args.result, args.evidence, args.lock_timeout)
        if cmd == "block":
            return block(md_path, json_path, args.id, args.reason, args.next_steps, args.lock_timeout)
        if cmd == "set-input":
            return set_input(md_path, json_path, args.text, args.lock_timeout)
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
