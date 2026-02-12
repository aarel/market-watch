#!/usr/bin/env python3
"""Start/stop/status for the dev server (background)."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _read_pid_info(pid_file: Path) -> dict | None:
    if not pid_file.exists():
        return None
    try:
        return json.loads(pid_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_pid_info(pid_file: Path, info: dict) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(json.dumps(info, indent=2), encoding="utf-8")


def _build_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        "scripts/serve.py",
        "--keyword",
        args.keyword,
    ]
    if args.host:
        cmd.extend(["--host", args.host])
    if args.port:
        cmd.extend(["--port", str(args.port)])
    if args.reload:
        cmd.append("--reload")
    if args.no_lifespan:
        cmd.append("--no-lifespan")
    if args.log_level:
        cmd.extend(["--log-level", args.log_level])
    if args.workers:
        cmd.extend(["--workers", str(args.workers)])
    return cmd


def start_server(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file)
    log_file = Path(args.log_file)
    info = _read_pid_info(pid_file)
    if info:
        pid = info.get("pid")
        if isinstance(pid, int) and _pid_running(pid):
            print(f"Dev server already running (pid {pid}).")
            print(f"Log file: {info.get('log_file')}")
            return 1
        pid_file.unlink(missing_ok=True)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_cmd(args)
    log_handle = log_file.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )
    info = {
        "pid": proc.pid,
        "started_at": datetime.now(UTC).isoformat(),
        "command": cmd,
        "log_file": str(log_file),
    }
    _write_pid_info(pid_file, info)
    print(f"Dev server started (pid {proc.pid}).")
    print(f"Log file: {log_file}")
    print(f"PID file: {pid_file}")
    return 0


def stop_server(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file)
    info = _read_pid_info(pid_file)
    if not info:
        print("Dev server not running (no PID file).")
        return 1
    pid = info.get("pid")
    if not isinstance(pid, int):
        print("PID file malformed.")
        return 1
    if not _pid_running(pid):
        print("Dev server not running.")
        pid_file.unlink(missing_ok=True)
        return 1

    os.kill(pid, signal.SIGTERM)
    for _ in range(20):
        if not _pid_running(pid):
            break
        time.sleep(0.25)
    if _pid_running(pid):
        os.kill(pid, signal.SIGKILL)
    pid_file.unlink(missing_ok=True)
    print(f"Dev server stopped (pid {pid}).")
    return 0


def status_server(args: argparse.Namespace) -> int:
    pid_file = Path(args.pid_file)
    info = _read_pid_info(pid_file)
    if not info:
        print("Dev server not running.")
        return 1
    pid = info.get("pid")
    if isinstance(pid, int) and _pid_running(pid):
        print(f"Dev server running (pid {pid}).")
        print(f"Log file: {info.get('log_file')}")
        return 0
    print("Dev server not running.")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Dev server control (background)")
    parser.add_argument("action", choices=("start", "stop", "status"))
    parser.add_argument("--host", default="", help="Host (defaults to API_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="Port (defaults to API_PORT or 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--no-lifespan", action="store_true", help="Disable lifespan startup")
    parser.add_argument("--log-level", default="", help="Uvicorn log level (info, debug, ...)")
    parser.add_argument("--workers", type=int, default=0, help="Uvicorn workers (requires reload off)")
    parser.add_argument("--keyword", default="activate market-watch", help="Safety keyword")
    parser.add_argument("--pid-file", default=str(REPO_ROOT / "logs" / "dev_server.pid"))
    parser.add_argument("--log-file", default=str(REPO_ROOT / "logs" / "dev_server.log"))
    args = parser.parse_args()

    if args.action == "start":
        return start_server(args)
    if args.action == "stop":
        return stop_server(args)
    return status_server(args)


if __name__ == "__main__":
    raise SystemExit(main())
