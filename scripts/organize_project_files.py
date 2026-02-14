"""Project scaffolder for repo hygiene (non-destructive moves)."""
from __future__ import annotations

import argparse
import os
import shutil
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class MovePlan:
    src: Path
    dest: Path
    reason: str


def _latest_timestamp(path: Path) -> datetime:
    stat = path.stat()
    candidates = [stat.st_mtime, stat.st_ctime]
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime:
        candidates.append(birthtime)
    ts = max(candidates)
    return datetime.fromtimestamp(ts)


def _date_bucket(path: Path) -> str:
    return _latest_timestamp(path).strftime("%Y-%m-%d")


def _plan_docs_archive() -> list[MovePlan]:
    docs_archive = REPO_ROOT / "docs" / "archive"
    if not docs_archive.exists():
        return []
    plans: list[MovePlan] = []
    for item in docs_archive.rglob("*"):
        if item.is_dir():
            continue
        date_bucket = _date_bucket(item)
        rel = item.relative_to(docs_archive)
        dest = REPO_ROOT / "development_docs" / "misc" / date_bucket / "docs_archive" / rel
        plans.append(MovePlan(item, dest, "docs_archive"))
    return plans


def _plan_tests_cleanup() -> list[MovePlan]:
    tests_root = REPO_ROOT / "tests"
    if not tests_root.exists():
        return []
    plans: list[MovePlan] = []
    for item in tests_root.iterdir():
        if item.is_dir():
            continue
        if item.suffix == ".py" or item.name == "README.md":
            continue
        date_bucket = _date_bucket(item)
        dest = REPO_ROOT / "test_results" / "legacy" / date_bucket / item.name
        plans.append(MovePlan(item, dest, "tests_cleanup"))
    return plans


def _plan_test_results_archive() -> list[MovePlan]:
    test_root = REPO_ROOT / "test_results"
    if not test_root.exists():
        return []
    plans: list[MovePlan] = []
    # Forward-only schema keeps new artifacts in timestamped run dirs.
    # This archiver targets only legacy flat files at test_results root.
    for item in test_root.iterdir():
        if item.is_dir():
            continue
        if not item.name.startswith("test_run_") and not item.name.endswith(".log"):
            continue
        date_bucket = _date_bucket(item)
        dest = test_root / "archive" / date_bucket / item.name
        plans.append(MovePlan(item, dest, "test_results_archive"))
    return plans


def _apply_moves(plans: Iterable[MovePlan]) -> list[MovePlan]:
    executed: list[MovePlan] = []
    for plan in plans:
        if not plan.src.exists():
            continue
        plan.dest.parent.mkdir(parents=True, exist_ok=True)
        if plan.dest.exists():
            continue
        shutil.move(str(plan.src), str(plan.dest))
        executed.append(plan)
    return executed


def _print_plan(plans: Iterable[MovePlan]) -> None:
    for plan in plans:
        print(f"{plan.reason}: {plan.src} -> {plan.dest}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize project files across folders.")
    parser.add_argument("--apply", action="store_true", help="Apply planned moves")
    parser.add_argument("--docs-archive", action="store_true", help="Move docs/archive into development_docs/misc/<date>/docs_archive/")
    parser.add_argument("--tests-cleanup", action="store_true", help="Move non-test files from tests/ into test_results/legacy/<date>/")
    parser.add_argument("--test-results", action="store_true", help="Archive loose test_results logs into test_results/archive/<date>/")
    parser.add_argument("--dev-docs", action="store_true", help="Run development_docs organizer (separate script)")
    args = parser.parse_args()

    plans: list[MovePlan] = []
    if args.docs_archive:
        plans.extend(_plan_docs_archive())
    if args.tests_cleanup:
        plans.extend(_plan_tests_cleanup())
    if args.test_results:
        plans.extend(_plan_test_results_archive())

    if plans:
        print("Planned moves:")
        _print_plan(plans)
    else:
        print("No moves planned.")

    if args.apply and plans:
        executed = _apply_moves(plans)
        print(f"Applied moves: {len(executed)}")
    elif args.apply:
        print("Nothing to apply.")

    if args.dev_docs:
        cmd = [str(REPO_ROOT / "venv" / "bin" / "python"), str(REPO_ROOT / "scripts" / "organize_development_docs.py"), "--apply", "--write-index", "--date-buckets", "all"]
        if not (REPO_ROOT / "venv" / "bin" / "python").exists():
            cmd = ["python", str(REPO_ROOT / "scripts" / "organize_development_docs.py"), "--apply", "--write-index", "--date-buckets", "all"]
        print("Running development_docs organizer...")
        os.system(" ".join(cmd))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
