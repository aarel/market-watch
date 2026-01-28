"""CLI entrypoint for observability evaluation."""
from __future__ import annotations

import argparse
import json
import os

from .evaluator import evaluate_log
from .report import render_report


def main():
    parser = argparse.ArgumentParser(description="Evaluate observability logs.")
    parser.add_argument("--log", default="logs/observability/agent_events.jsonl", help="Path to JSONL log file")
    parser.add_argument("--since", default=None, help="ISO timestamp cutoff (inclusive)")
    parser.add_argument("--expectations", default=None, help="Path to expectations JSON")
    parser.add_argument("--output", default="logs/observability/latest_eval.json", help="Output JSON path")
    parser.add_argument("--report", default="logs/observability/latest_report.txt", help="Output report text path")

    args = parser.parse_args()

    report = evaluate_log(args.log, since=args.since, expectations_path=args.expectations)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2)

    report_text = render_report(report)
    with open(args.report, "w", encoding="utf-8") as handle:
        handle.write(report_text)

    print(report_text)


if __name__ == "__main__":
    main()
