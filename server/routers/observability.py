import json
import os
from typing import Optional

from fastapi import APIRouter, Depends

import config
from ..dependencies import get_state

router = APIRouter()


@router.get("/observability")
async def get_observability_status(state=Depends(get_state)):
    """Returns observability system status and latest evaluation"""
    if not config.OBSERVABILITY_ENABLED:
        return {"enabled": False, "status": "disabled"}

    observability = state.observability or {}
    return {
        "enabled": True,
        "status": "ok",
        "latest": observability,
        "expectations": []
    }


@router.get("/observability/logs")
async def get_observability_logs(limit: int = 30, level: Optional[str] = "warn", state=Depends(get_state)):
    path = config.OBSERVABILITY_LOG_PATH
    limit = max(1, min(limit, 200))
    if not path or not os.path.exists(path):
        return {"logs": []}

    def _level_match(entry):
        if not level:
            return True
        outcome = (entry.get("outcome") or "").lower()
        if level == "warn":
            return outcome in ("warn", "fail", "error")
        return True

    entries = []
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()[-limit * 3 :]
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not _level_match(obj):
            continue
        entries.append(
            {
                "timestamp": obj.get("timestamp"),
                "agent": obj.get("agent"),
                "event_type": obj.get("event_type"),
                "action": obj.get("action"),
                "symbol": obj.get("symbol"),
                "outcome": obj.get("outcome"),
                "reason": obj.get("reason"),
                "context": obj.get("context", {}),
            }
        )
        if len(entries) >= limit:
            break
    return {"logs": list(reversed(entries))}
