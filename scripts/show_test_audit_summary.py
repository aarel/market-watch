#!/usr/bin/env python3
"""Show the latest test audit summary and coverage report snippet."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _find_latest_run() -> Path | None:
    root = REPO_ROOT / "test_results" / "test_audit"
    if not root.exists():
        return None
    runs = [p for p in root.iterdir() if p.is_dir()]
    if not runs:
        return None
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]


def _load_summary(run_dir: Path) -> dict | None:
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _print_list(label: str, items: list[str], limit: int) -> None:
    print(f"{label}: {len(items)}")
    if not items:
        return
    for item in items[:limit]:
        print(f"  - {item}")
    if len(items) > limit:
        print(f"  ... {len(items) - limit} more")


def main() -> int:
    parser = argparse.ArgumentParser(description="Show latest test audit summary.")
    parser.add_argument("--run-dir", default="", help="Specific test audit run dir to inspect")
    parser.add_argument("--tail", type=int, default=0, help="Show last N lines of coverage report")
    parser.add_argument("--full", action="store_true", help="Show full coverage report")
    parser.add_argument("--list-files", action="store_true", help="List missing/zero/low coverage files")
    parser.add_argument("--limit", type=int, default=20, help="Max files to list per category")
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else _find_latest_run()
    if not run_dir or not run_dir.exists():
        print("No test audit run found. Run: ./venv/bin/python scripts/run_test_audit.py")
        return 1

    summary = _load_summary(run_dir)
    print(f"Latest test audit: {run_dir}")
    if summary:
        print(f"Timestamp: {summary.get('timestamp')}")
        cov = summary.get("coverage") or {}
        if cov:
            print(f"Coverage: {cov.get('covered_percent')}%")
            print(f"Missing files: {len(cov.get('missing_files', []))}")
            print(f"Zero coverage files: {len(cov.get('zero_coverage_files', []))}")
            print(f"Low coverage files (<50%): {len(cov.get('low_coverage_files', []))}")
            if args.list_files:
                _print_list("Missing files", cov.get("missing_files", []), args.limit)
                _print_list("Zero coverage files", cov.get("zero_coverage_files", []), args.limit)
                _print_list("Low coverage files", cov.get("low_coverage_files", []), args.limit)
        test = summary.get("test_validity") or {}
        if test:
            print(f"Tests without asserts: {len(test.get('tests_without_asserts', []))}")
            print(f"Skipped tests: {len(test.get('skipped_tests', []))}")
            print(f"Xfailed tests: {len(test.get('xfailed_tests', []))}")
            print(f"Empty tests: {len(test.get('empty_tests', []))}")
    else:
        print("Summary.json not found or unreadable.")

    coverage_report = run_dir / "coverage_report.txt"
    if args.full and coverage_report.exists():
        print("")
        print("Coverage report:")
        print(coverage_report.read_text(encoding="utf-8"))
    elif args.tail and coverage_report.exists():
        lines = coverage_report.read_text(encoding="utf-8").splitlines()
        tail = lines[-args.tail:] if len(lines) > args.tail else lines
        print("")
        print(f"Coverage report (last {len(tail)} lines):")
        print("\n".join(tail))
    elif (args.full or args.tail) and not coverage_report.exists():
        print("")
        print("Coverage report not found. Run test audit with coverage enabled.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
