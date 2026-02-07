"""Plan/apply development_docs scaffolding without deleting files."""
from __future__ import annotations

import argparse
from pathlib import Path

from agents.dev.docs_scaffold_agent import DocScaffoldPlanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize development_docs into categories.")
    parser.add_argument("--apply", action="store_true", help="Apply planned moves")
    parser.add_argument("--include-directories", action="store_true", help="Include directories in move plan")
    parser.add_argument("--write-index", action="store_true", help="Write development_docs/README.md index")
    args = parser.parse_args()

    planner = DocScaffoldPlanner()
    plans = planner.build_plan(include_directories=args.include_directories)
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
