"""Plan/apply development_docs scaffolding without deleting files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.dev.docs_scaffold_agent import DocScaffoldPlanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize development_docs into categories.")
    parser.add_argument("--apply", action="store_true", help="Apply planned moves")
    parser.add_argument("--include-directories", action="store_true", help="Include directories in move plan")
    parser.add_argument("--write-index", action="store_true", help="Write development_docs/README.md index")
    parser.add_argument(
        "--date-buckets",
        default="",
        help="Comma-separated category names to bucket by date (e.g., audits,reports) or 'all'",
    )
    args = parser.parse_args()

    date_bucket_categories = [c.strip() for c in args.date_buckets.split(",") if c.strip()]

    planner = DocScaffoldPlanner()
    plans = planner.build_plan(
        include_directories=args.include_directories,
        date_bucket_categories=date_bucket_categories,
    )
    plan_path = planner.write_plan(plans)
    print(f"Plan saved to: {plan_path}")
    print(f"Planned moves: {len(plans)}")

    if args.apply:
        planner.apply_plan(plans)
        print("Moves applied.")

    if args.write_index:
        index_path = planner.write_index()
        print(f"Index written: {index_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
