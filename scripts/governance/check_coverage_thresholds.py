#!/usr/bin/env python3
"""Coverage threshold gate for CI.

Checks:
- overall line coverage floor
- overall branch coverage floor
- server/ line coverage floor
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def aggregate_prefix(files: dict, prefix: str) -> tuple[int, int, int, int]:
    total_statements = 0
    missing_lines = 0
    total_branches = 0
    missing_branches = 0
    for path, meta in files.items():
        if not path.startswith(prefix):
            continue
        summary = meta.get("summary", {})
        total_statements += int(summary.get("num_statements", 0))
        missing_lines += int(summary.get("missing_lines", 0))
        total_branches += int(summary.get("num_branches", 0))
        missing_branches += int(summary.get("missing_branches", 0))
    return total_statements, missing_lines, total_branches, missing_branches


def pct(total: int, missing: int) -> float:
    if total <= 0:
        return 0.0
    return ((total - missing) / total) * 100.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="coverage.json")
    parser.add_argument("--min-line", type=float, default=75.0)
    parser.add_argument("--min-branch", type=float, default=65.0)
    parser.add_argument("--min-server-line", type=float, default=60.0)
    args = parser.parse_args()

    coverage_path = Path(args.input)
    if not coverage_path.exists():
        raise SystemExit(f"coverage input missing: {coverage_path}")

    payload = json.loads(coverage_path.read_text(encoding="utf-8"))
    totals = payload.get("totals", {})
    files = payload.get("files", {})

    overall_line = float(totals.get("percent_covered", 0.0))
    overall_branch = float(totals.get("percent_branches_covered", 0.0))

    s_statements, s_missing, _s_branches, _s_missing_branches = aggregate_prefix(files, "server/")
    server_line = pct(s_statements, s_missing)

    failures: list[str] = []
    if overall_line < args.min_line:
        failures.append(f"overall line coverage {overall_line:.2f}% < {args.min_line:.2f}%")
    if overall_branch < args.min_branch:
        failures.append(f"overall branch coverage {overall_branch:.2f}% < {args.min_branch:.2f}%")
    if server_line < args.min_server_line:
        failures.append(f"server/ line coverage {server_line:.2f}% < {args.min_server_line:.2f}%")

    print(f"overall_line={overall_line:.2f}% overall_branch={overall_branch:.2f}% server_line={server_line:.2f}%")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print("PASS: coverage thresholds satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
