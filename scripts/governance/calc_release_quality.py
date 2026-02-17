#!/usr/bin/env python3
"""Compute release quality KPIs: deployment lead time + change failure rate.

Input JSON format:
{
  "deployments": [
    {
      "id": "deploy-001",
      "merge_time": "2026-02-14T10:00:00Z",
      "deploy_time": "2026-02-14T12:00:00Z",
      "failed": false,
      "rollback": false,
      "hotfix": false
    }
  ]
}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def parse_ts(value: str) -> dt.datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return dt.datetime.fromisoformat(raw)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * p))
    return ordered[idx]


def compute(payload: dict) -> dict:
    deployments = payload.get("deployments", [])
    lead_times_hours: list[float] = []
    failures = 0

    for d in deployments:
        merge_time = d.get("merge_time")
        deploy_time = d.get("deploy_time")
        if merge_time and deploy_time:
            delta = parse_ts(deploy_time) - parse_ts(merge_time)
            lead_times_hours.append(max(delta.total_seconds() / 3600.0, 0.0))

        if bool(d.get("failed")) or bool(d.get("rollback")) or bool(d.get("hotfix")):
            failures += 1

    total = len(deployments)
    cfr = (failures / total) if total else 0.0

    return {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "totals": {
            "deployments": total,
            "failures": failures,
        },
        "lead_time_hours": {
            "p50": round(percentile(lead_times_hours, 0.50), 3),
            "p90": round(percentile(lead_times_hours, 0.90), 3),
            "mean": round((sum(lead_times_hours) / len(lead_times_hours)) if lead_times_hours else 0.0, 3),
        },
        "change_failure_rate": {
            "ratio": round(cfr, 4),
            "percent": round(cfr * 100.0, 2),
        },
        "targets": {
            "lead_time_p50_hours_max": 24,
            "lead_time_p90_hours_max": 72,
            "change_failure_rate_percent_max": 15,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="reports/governance/deployments.json")
    parser.add_argument("--out", default="reports/governance/release_quality.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    result = compute(payload)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
