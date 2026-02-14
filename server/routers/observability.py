import csv
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from monitoring.anomaly_detector import get_detector
from universe import get_system_log_path

from ..runtime.demo_hardening import get_safe_universe_context

router = APIRouter()

_EST = ZoneInfo("America/New_York")
_CSV_DIR = "logs/risk-and-obs-alerts"
_CSV_FIELDS = ["timestamp", "agent", "event_type", "action", "symbol", "outcome", "reason"]


def _today_est() -> str:
    """Return today's date in NY EST as ISO string (YYYY-MM-DD)."""
    return datetime.now(_EST).strftime("%Y-%m-%d")


def _write_daily_csv(warn_fail_entries: list[dict], date_str: str):
    """Overwrite today's CSV with the full day's warn/fail entries."""
    if not warn_fail_entries:
        return
    os.makedirs(_CSV_DIR, exist_ok=True)
    path = os.path.join(_CSV_DIR, f"{date_str.replace('-', '')}_risk_obs.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(warn_fail_entries)


@router.get("/observability/logs")
async def get_observability_logs(level: str | None = "warn", ctx=Depends(get_safe_universe_context)):
    path = get_system_log_path(ctx.universe, "agent_events.jsonl")
    if not os.path.exists(path):
        return {"logs": []}

    today = _today_est()  # e.g. "2026-02-05" in NY time

    with open(path, encoding="utf-8") as handle:
        lines = handle.readlines()

    entries = []  # all warn/fail today

    # Events are chronological; scan from the end and stop at yesterday
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue

        timestamp = obj.get("timestamp") or ""
        if not timestamp.startswith(today):
            break  # past today, done

        outcome = (obj.get("outcome") or "").lower()

        if outcome in ("warn", "fail", "error"):
            entries.append({
                "timestamp": timestamp,
                "agent": obj.get("agent"),
                "event_type": obj.get("event_type"),
                "action": obj.get("action"),
                "symbol": obj.get("symbol"),
                "outcome": obj.get("outcome"),
                "reason": obj.get("reason"),
                "context": obj.get("context", {}),
            })

    entries.reverse()  # chronological order

    # Persist today's warn/fail to daily CSV (overwrite; filename rotates at midnight EST)
    _write_daily_csv(entries, today)

    return {"logs": entries}


@router.get("/observability/anomalies")
async def get_anomaly_status():
    """
    Get current anomaly detection status.

    Returns:
        - status: Current detector status with event rates
        - anomaly: Detected anomaly details if any
    """
    detector = get_detector()
    status = detector.get_status()
    anomaly = detector.detect_anomaly()

    return {
        "status": status,
        "anomaly": anomaly
    }


@router.post("/observability/baseline")
async def update_baseline():
    """
    Update anomaly detection baseline.

    Should be called periodically during normal operation to establish
    what "normal" event rates look like.
    """
    detector = get_detector()
    detector.update_baseline()

    return {"message": "Baseline updated", "status": detector.get_status()}
