#!/usr/bin/env python3
"""Thin orchestrator for communicate lifecycle.

This layer has no state logic. It only invokes communicate_scan.py transitions.
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="commscribe/communicate.md")
    parser.add_argument("--json", default="commscribe/communicate.json")
    parser.add_argument("--failure-log", default="commscribe/failure_log.json")
    parser.add_argument("--lock-timeout", type=int, default=5)
    parser.add_argument("--plan", default="Evaluate request and execute repository changes with evidence.")
    parser.add_argument("--exec-cmd", default="")
    return parser.parse_args()


def _scan_cmd(script: Path, args: argparse.Namespace, *parts: str) -> list[str]:
    cmd = [
        "python3",
        str(script),
        "--file",
        args.file,
        "--json",
        args.json,
        "--failure-log",
        args.failure_log,
        "--lock-timeout",
        str(args.lock_timeout),
    ]
    cmd.extend(parts)
    return cmd


def main() -> int:
    args = parse_args()
    scan_script = Path(__file__).with_name("communicate_scan.py")

    status = _run(_scan_cmd(scan_script, args, "system-status"))
    if status.returncode == 2:
        sys.stderr.write(status.stderr or "SYSTEM_BLOCKED\n")
        return 2
    if status.returncode != 0:
        sys.stderr.write(status.stderr)
        return status.returncode

    consume = _run(_scan_cmd(scan_script, args, "consume"))
    if consume.returncode != 0:
        sys.stderr.write(consume.stderr)
        return consume.returncode

    out = consume.stdout.strip()
    if "No new INPUT PAD content" in out:
        print(out)
        return 0

    match = re.search(r"REQ-[^\s]+", out)
    if not match:
        sys.stderr.write("ERROR: consume did not return a request id\n")
        return 1
    req_id = match.group(0)

    ack = _run(_scan_cmd(scan_script, args, "ack", "--id", req_id, "--plan", args.plan))
    if ack.returncode != 0:
        sys.stderr.write(ack.stderr)
        return ack.returncode

    log_start = _run(_scan_cmd(scan_script, args, "log", "--id", req_id, "--message", "Orchestrator started execution."))
    if log_start.returncode != 0:
        sys.stderr.write(log_start.stderr)
        return log_start.returncode

    if not args.exec_cmd.strip():
        blocked = _run(
            _scan_cmd(
                scan_script,
                args,
                "block",
                "--id",
                req_id,
                "--reason",
                "No --exec-cmd provided.",
                "--next-steps",
                "Provide an explicit execution command or process manually.",
            )
        )
        if blocked.returncode != 0:
            sys.stderr.write(blocked.stderr)
            return blocked.returncode
        print(f"{req_id} BLOCKED")
        return 0

    exec_result = _run(shlex.split(args.exec_cmd))
    evidence = f"exec_cmd={args.exec_cmd}\nstdout={exec_result.stdout.strip()}\nstderr={exec_result.stderr.strip()}"

    if exec_result.returncode == 0:
        done = _run(
            _scan_cmd(
                scan_script,
                args,
                "complete",
                "--id",
                req_id,
                "--result",
                "Execution command finished successfully.",
                "--evidence",
                evidence,
            )
        )
        if done.returncode != 0:
            sys.stderr.write(done.stderr)
            return done.returncode
        print(f"{req_id} DONE")
        return 0

    blocked = _run(
        _scan_cmd(
            scan_script,
            args,
            "block",
            "--id",
            req_id,
            "--reason",
            f"Execution command failed with exit code {exec_result.returncode}.",
            "--next-steps",
            "Inspect captured stderr and rerun with corrected command.",
        )
    )
    if blocked.returncode != 0:
        sys.stderr.write(blocked.stderr)
        return blocked.returncode
    print(f"{req_id} BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
