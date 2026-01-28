"""UICheckAgent - lightweight UI smoke test using HTTP fetch and selector checks."""
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

import requests

from .base import BaseAgent
from .events import LogEvent
import config
from monitoring.logger import SystemLogWriter
from universe import Universe


class UICheckAgent(BaseAgent):
    """Periodically fetches the UI and checks for key elements."""

    def __init__(self, event_bus, interval_minutes: int = 30, url: Optional[str] = None, log_path: Optional[str] = None):
        super().__init__("UICheckAgent", event_bus)
        self.interval_minutes = max(5, interval_minutes)
        self.url = url or f"http://{config.API_HOST}:{config.UI_PORT}"
        filename = (log_path.split("/")[-1] if log_path else "ui_checks.jsonl")
        self._log_writer = SystemLogWriter(self.universe, filename=filename)
        self._task = None

    async def start(self):
        await super().start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await super().stop()

    async def _loop(self):
        await asyncio.sleep(5)
        while self.running:
            try:
                self._check_once()
            except Exception as exc:
                await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="warning", message=f"UI check error: {exc}"))
            await asyncio.sleep(self.interval_minutes * 60)

    def _check_once(self):
        started = datetime.now(timezone.utc)
        status = "ok"
        detail = {}
        try:
            resp = requests.get(self.url, timeout=10)
            detail["status_code"] = resp.status_code
            html = resp.text
            # simple selector presence checks
            detail["has_metric_return"] = "metric-return" in html
            detail["has_pie_chart"] = "position-pie-chart" in html
            detail["has_trades_table"] = "analytics-trades" in html
            if resp.status_code != 200 or not (detail["has_metric_return"] and detail["has_pie_chart"] and detail["has_trades_table"]):
                status = "warn"
        except Exception as exc:
            status = "error"
            detail["error"] = str(exc)

        entry = {
            "timestamp": started.isoformat(),
            "url": self.url,
            "status": status,
            "detail": detail,
        }
        self._log_writer.write(entry)

        level = "info" if status == "ok" else "warning"
        self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level=level, message=f"UI check {status}"))
