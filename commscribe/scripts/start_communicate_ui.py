#!/usr/bin/env python3
"""Local UI for communicate.md."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import mimetypes
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
COMMSCRIBE_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = COMMSCRIBE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from commscribe.api.requests_api import RequestAPI


def _resolve_runtime_path(raw: str) -> Path:
    """Resolve a CLI path robustly across different launch directories."""
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate

    cwd_candidate = (Path.cwd() / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    project_candidate = (PROJECT_ROOT / candidate).resolve()
    if project_candidate.exists():
        return project_candidate

    commscribe_candidate = (COMMSCRIBE_DIR / candidate).resolve()
    if commscribe_candidate.exists():
        return commscribe_candidate

    # Keep legacy defaults under project root (e.g., "commscribe/ui/index.html").
    if str(candidate).startswith("commscribe/"):
        return project_candidate
    return commscribe_candidate


def write_input_pad_via_scan(
    scan_script: Path,
    communicate_file: Path,
    json_file: Path,
    failure_log_file: Path,
    text: str,
    lock_timeout: int,
    db_path: Path | None = None,
    schema_path: Path | None = None,
) -> None:
    cmd = [
        sys.executable,
        str(scan_script),
        "--file",
        str(communicate_file),
        "--json",
        str(json_file),
    ]
    if db_path is not None:
        cmd.extend(["--db", str(db_path)])
    if schema_path is not None:
        cmd.extend(["--schema", str(schema_path)])
    cmd.extend(
        [
        "--failure-log",
        str(failure_log_file),
        "--lock-timeout",
        str(lock_timeout),
        "set-input",
        "--text",
        text,
        ]
    )
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "set-input failed"
        raise RuntimeError(message)


def load_requests_from_json(json_file: Path) -> list[dict]:
    if not json_file.exists():
        return []
    payload = json.loads(json_file.read_text(encoding="utf-8"))
    requests = payload.get("requests", [])
    if not isinstance(requests, list):
        return []
    return requests


def selected_req_from_url(url: str) -> str:
    split = urlsplit(url)
    query_id = parse_qs(split.query).get("req", [""])[0].strip()
    if query_id:
        return query_id
    fragment = split.fragment.strip()
    if fragment.startswith("/"):
        fragment = fragment[1:]
    if fragment.upper().startswith("REQ-"):
        return fragment
    return ""


class Handler(BaseHTTPRequestHandler):
    ui_file: Path
    communicate_file: Path
    json_file: Path
    scan_script: Path
    failure_log_file: Path
    db_path: Path
    schema_path: Path
    lock_timeout: int
    request_api: RequestAPI

    def _serve_static_asset(self, path: str) -> bool:
        if path.startswith("/api/"):
            return False
        ui_root = self.ui_file.parent.resolve()
        candidate = (ui_root / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(ui_root)):
            return False
        if not candidate.exists() or not candidate.is_file():
            return False
        content = candidate.read_bytes()
        content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def _send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        split = urlsplit(self.path)
        path = split.path

        if path in {"/", "/communicate"}:
            content = self.ui_file.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if self._serve_static_asset(path):
            return

        if path == "/api/thread":
            text = self.request_api.export_markdown()
            input_pad = self.request_api.get_input_pad()
            self._send_json(
                {
                    "input_pad": input_pad,
                    "document": text,
                    "selected_req": selected_req_from_url(self.path),
                }
            )
            return

        if path == "/api/requests":
            params = parse_qs(split.query)
            req_date = (params.get("date", [""])[0] or "").strip()
            source = (params.get("source", ["communicate>"])[0] or "").strip()
            diagnostics_on = (params.get("diagnostics", ["0"])[0] or "").strip().lower() in {"1", "true", "yes"}
            if not req_date:
                req_date = dt.datetime.now(dt.timezone.utc).date().isoformat()
            requests = self.request_api.get_all_requests(
                include_archived=False,
                created_date=req_date,
                source=source or None,
            )
            summary = [
                {
                    "id": r.get("id", ""),
                    "request_id": r.get("id", ""),
                    "title": r.get("title", ""),
                    "status": r.get("status", ""),
                    "created_at": r.get("created_at", ""),
                    "updated_at": r.get("updated_at", ""),
                    "last_updated_at": r.get("updated_at", ""),
                }
                for r in requests
            ]
            diagnostics = None
            if diagnostics_on:
                source_rows = self.request_api.get_all_requests(
                    include_archived=True,
                    created_date=None,
                    source=source or None,
                )
                diagnostics = {
                    "db_path": str(self.db_path),
                    "source_filter": source,
                    "filtered_row_count": len(summary),
                    "source_row_count": len(source_rows),
                    "latest_request_ids": [r.get("id", "") for r in source_rows[:5]],
                }
            self._send_json(
                {
                    "requests": summary,
                    "selected_req": selected_req_from_url(self.path),
                    "date": req_date,
                    "source": source,
                    "diagnostics": diagnostics,
                }
            )
            return

        if path.startswith("/api/request/"):
            req_id = unquote(path.removeprefix("/api/request/")).strip()
            req = self.request_api.get_request(req_id)
            if req is not None:
                payload = dict(req)
                payload.setdefault("request_id", payload.get("id", req_id))
                payload.setdefault("last_updated_at", payload.get("updated_at", ""))
                self._send_json({"request": payload, "selected_req": req_id})
                return
            self._send_json({"error": f"unknown request id: {req_id}"}, status=404)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/input":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return

        text = str(payload.get("text", "")).strip()
        if not text:
            self._send_json({"error": "text is required"}, status=400)
            return

        try:
            write_input_pad_via_scan(
                scan_script=self.scan_script,
                communicate_file=self.communicate_file,
                json_file=self.json_file,
                failure_log_file=self.failure_log_file,
                text=text,
                lock_timeout=self.lock_timeout,
                db_path=self.db_path,
                schema_path=self.schema_path,
            )
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": str(exc)}, status=400)
            return
        self._send_json({"ok": True})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--communicate", default="commscribe/communicate.md")
    parser.add_argument("--json", default="commscribe/communicate.json")
    parser.add_argument("--db", default="commscribe/db/communicate.db")
    parser.add_argument("--schema", default="commscribe/db/schema.sql")
    parser.add_argument("--failure-log", default="commscribe/failure_log.json")
    parser.add_argument("--lock-timeout", type=int, default=5)
    parser.add_argument("--ui", default="commscribe/ui/index.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    Handler.ui_file = _resolve_runtime_path(args.ui)
    Handler.communicate_file = _resolve_runtime_path(args.communicate)
    Handler.json_file = _resolve_runtime_path(args.json)
    Handler.scan_script = (SCRIPT_DIR / "communicate_scan.py").resolve()
    Handler.failure_log_file = _resolve_runtime_path(args.failure_log)
    Handler.db_path = _resolve_runtime_path(args.db)
    Handler.schema_path = _resolve_runtime_path(args.schema)
    Handler.lock_timeout = int(args.lock_timeout)
    Handler.request_api = RequestAPI.from_env_or_args(
        json_file=Handler.json_file,
        db_path=Handler.db_path,
        schema_path=Handler.schema_path,
    )
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving UI on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
