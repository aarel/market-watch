#!/usr/bin/env python3
"""Generate coverage gap report from coverage.json.

Outputs:
- reports/coverage/gap_report.json
- reports/coverage/gap_report.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CRITICAL_TARGETS = {
    "server/": {"line_target": 72.0, "branch_target": 55.0},
    "scripts/governance/": {"line_target": 80.0, "branch_target": 70.0},
    "commscribe/scripts/": {"line_target": 80.0, "branch_target": 70.0},
}


def aggregate_prefix(files: dict, prefix: str) -> dict:
    statements = missing = branches = missing_branches = 0
    for path, meta in files.items():
        if path.startswith(prefix):
            s = meta.get("summary", {})
            statements += int(s.get("num_statements", 0))
            missing += int(s.get("missing_lines", 0))
            branches += int(s.get("num_branches", 0))
            missing_branches += int(s.get("missing_branches", 0))
    line_cov = ((statements - missing) / statements * 100.0) if statements else None
    branch_cov = ((branches - missing_branches) / branches * 100.0) if branches else None
    return {
        "statements": statements,
        "missing_lines": missing,
        "line_percent": round(line_cov, 2) if line_cov is not None else None,
        "branches": branches,
        "missing_branches": missing_branches,
        "branch_percent": round(branch_cov, 2) if branch_cov is not None else None,
        "measured": bool(statements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="coverage.json")
    parser.add_argument("--json-out", default="reports/coverage/gap_report.json")
    parser.add_argument("--md-out", default="reports/coverage/gap_report.md")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"coverage input missing: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    files = payload.get("files", {})
    totals = payload.get("totals", {})

    ranked = []
    for path, meta in files.items():
        summary = meta.get("summary", {})
        ranked.append(
            {
                "path": path,
                "missing_lines": int(summary.get("missing_lines", 0)),
                "line_percent": float(summary.get("percent_covered", 0.0)),
                "num_statements": int(summary.get("num_statements", 0)),
                "missing_branches": int(summary.get("missing_branches", 0)),
                "branch_percent": float(summary.get("percent_branches_covered", 0.0)),
            }
        )

    ranked.sort(key=lambda x: (x["missing_lines"], x["missing_branches"]), reverse=True)
    top = ranked[: args.top]

    critical = {}
    for prefix, targets in CRITICAL_TARGETS.items():
        actual = aggregate_prefix(files, prefix)
        critical[prefix] = {
            **actual,
            "line_target": targets["line_target"],
            "branch_target": targets["branch_target"],
            "line_gap": round(targets["line_target"] - actual["line_percent"], 2) if actual["line_percent"] is not None else None,
            "branch_gap": round(targets["branch_target"] - actual["branch_percent"], 2) if actual["branch_percent"] is not None else None,
        }

    report = {
        "overall": {
            "line_percent": totals.get("percent_covered", 0.0),
            "branch_percent": totals.get("percent_branches_covered", 0.0),
            "num_statements": totals.get("num_statements", 0),
            "missing_lines": totals.get("missing_lines", 0),
        },
        "top_missing_files": top,
        "critical_modules": critical,
    }

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)

    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Coverage Gap Report",
        "",
        f"- Overall line coverage: {report['overall']['line_percent']:.2f}%",
        f"- Overall branch coverage: {report['overall']['branch_percent']:.2f}%",
        "",
        "## Critical Modules",
        "",
        "| Module | Line % | Line Target | Branch % | Branch Target |",
        "|---|---:|---:|---:|---:|",
    ]
    for module, values in critical.items():
        line_pct = "n/a" if values["line_percent"] is None else f"{values['line_percent']:.2f}"
        branch_pct = "n/a" if values["branch_percent"] is None else f"{values['branch_percent']:.2f}"
        lines.append(
            f"| {module} | {line_pct} | {values['line_target']:.2f} | {branch_pct} | {values['branch_target']:.2f} |"
        )

    lines.extend([
        "",
        f"## Top {args.top} Files by Missed Lines",
        "",
        "| File | Missed Lines | Line % | Missed Branches | Branch % |",
        "|---|---:|---:|---:|---:|",
    ])
    for row in top:
        lines.append(
            f"| {row['path']} | {row['missing_lines']} | {row['line_percent']:.2f} | {row['missing_branches']} | {row['branch_percent']:.2f} |"
        )

    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {json_out}")
    print(f"Wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
