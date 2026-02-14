#!/usr/bin/env python3
"""Local UI for communicate.md."""

from __future__ import annotations

import argparse
import json
import mimetypes
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from communicate_scan import INPUT_END, INPUT_START, _section


def write_input_pad_via_scan(
    scan_script: Path,
    communicate_file: Path,
    json_file: Path,
    failure_log_file: Path,
    text: str,
    lock_timeout: int,
) -> None:
    cmd = [
        sys.executable,
        str(scan_script),
        "--file",
        str(communicate_file),
        "--json",
        str(json_file),
        "--failure-log",
        str(failure_log_file),
        "--lock-timeout",
        str(lock_timeout),
        "set-input",
        "--text",
        text,
    ]
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
    failure_log_file: Path
    scan_script: Path
    lock_timeout: int

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

    def _read_communicate(self) -> str:
        return self.communicate_file.read_text(encoding="utf-8")

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
            text = self._read_communicate()
            input_pad = _section(text, INPUT_START, INPUT_END).strip()
            self._send_json(
                {
                    "input_pad": input_pad,
                    "document": text,
                    "selected_req": selected_req_from_url(self.path),
                }
            )
            return

        if path == "/api/requests":
            requests = load_requests_from_json(self.json_file)
            summary = [
                {
                    "request_id": r.get("request_id", ""),
                    "status": r.get("status", ""),
                    "created_at": r.get("created_at", ""),
                    "last_updated_at": r.get("last_updated_at", ""),
                }
                for r in requests
            ]
            self._send_json({"requests": summary, "selected_req": selected_req_from_url(self.path)})
            return

        if path.startswith("/api/request/"):
            req_id = unquote(path.removeprefix("/api/request/")).strip()
            requests = load_requests_from_json(self.json_file)
            for req in requests:
                if req.get("request_id") == req_id:
                    self._send_json({"request": req, "selected_req": req_id})
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
            )
        except RuntimeError as exc:
            self._send_json({"error": str(exc)}, status=409)
            return
        self._send_json({"ok": True})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--communicate", default="commscribe/communicate.md")
    parser.add_argument("--json", default="commscribe/communicate.json")
    parser.add_argument("--failure-log", default="commscribe/failure_log.json")
    parser.add_argument("--lock-timeout", type=int, default=5)
    parser.add_argument("--scan-script", default=None)
    parser.add_argument("--ui", default="commscribe/ui/index.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scan_script = Path(args.scan_script) if args.scan_script else Path(__file__).with_name("communicate_scan.py")
    Handler.ui_file = Path(args.ui)
    Handler.communicate_file = Path(args.communicate)
    Handler.json_file = Path(args.json)
    Handler.failure_log_file = Path(args.failure_log)
    Handler.scan_script = scan_script
    Handler.lock_timeout = args.lock_timeout
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving UI on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
