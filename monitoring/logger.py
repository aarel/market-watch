"""JSONL logger for structured observability events."""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from universe import Universe, get_system_log_path


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


class SystemLogWriter:
    """Universe-scoped system/observability logger with rotation."""

    def __init__(self, universe: Universe, filename: str = "agent_events.jsonl", max_mb: float = 5.0, base_dir: Path | None = None):
        self.universe = universe
        base = base_dir or Path(".")
        self.path = base / get_system_log_path(universe, filename)
        self.max_bytes = int(max_mb * 1024 * 1024) if max_mb else 0
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]):
        """Append a JSON line to the universe-scoped log file."""
        if record.get("universe") not in (None, self.universe.value):
            raise ValueError(f"System log universe mismatch: got {record.get('universe')}, expected {self.universe.value}")
        record = dict(record)
        record.setdefault("universe", self.universe.value)
        self._rotate_if_needed()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True, default=_json_default))
            handle.write("\n")

    def _rotate_if_needed(self):
        if not self.max_bytes:
            return
        if not self.path.exists():
            return
        if self.path.stat().st_size <= self.max_bytes:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = self.path.with_suffix(self.path.suffix + f".{timestamp}")
        os.rename(self.path, rotated)
