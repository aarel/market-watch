"""JSONL logger for structured observability events."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class JSONLLogger:
    """Append-only JSONL logger with simple size rotation."""

    def __init__(self, path: str, max_mb: float = 5.0):
        self.path = path
        self.max_bytes = int(max_mb * 1024 * 1024) if max_mb else 0
        log_dir = os.path.dirname(path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

    def write(self, record: dict[str, Any]):
        """Append a JSON line to the log file."""
        self._rotate_if_needed()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, default=_json_default))
            handle.write("\n")

    def _rotate_if_needed(self):
        if not self.max_bytes:
            return
        if not os.path.exists(self.path):
            return
        if os.path.getsize(self.path) <= self.max_bytes:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = f"{self.path}.{timestamp}"
        os.rename(self.path, rotated)


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
