#!/usr/bin/env python3
"""Fail when release quality KPIs exceed configured targets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="reports/governance/release_quality.json")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        raise SystemExit(f"KPI file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    lead = payload.get("lead_time_hours", {})
    cfr = payload.get("change_failure_rate", {})
    targets = payload.get("targets", {})

    failures: list[str] = []

    p50 = float(lead.get("p50", 0.0))
    p90 = float(lead.get("p90", 0.0))
    cfr_pct = float(cfr.get("percent", 0.0))

    p50_max = float(targets.get("lead_time_p50_hours_max", 24.0))
    p90_max = float(targets.get("lead_time_p90_hours_max", 72.0))
    cfr_max = float(targets.get("change_failure_rate_percent_max", 15.0))

    if p50 > p50_max:
        failures.append(f"lead_time p50 breach: {p50} > {p50_max}")
    if p90 > p90_max:
        failures.append(f"lead_time p90 breach: {p90} > {p90_max}")
    if cfr_pct > cfr_max:
        failures.append(f"change_failure_rate breach: {cfr_pct}% > {cfr_max}%")

    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1

    print("PASS: governance thresholds within targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
