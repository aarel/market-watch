"""SessionLoggerAgent - periodically logs SIM session snapshots for training/replay analysis."""
import asyncio
import json
import os
from datetime import datetime
from typing import Optional

from .base import BaseAgent
from .events import LogEvent
import config
from universe import Universe
from monitoring.logger import SystemLogWriter


class SessionLoggerAgent(BaseAgent):
    """Logs account/positions summary to JSONL for SIM training analysis."""

    def __init__(self, event_bus, broker, interval_minutes: int = 10, log_path: Optional[str] = None):
        super().__init__("SessionLoggerAgent", event_bus)
        self.broker = broker
        self.interval_minutes = max(1, interval_minutes)
        self._log_writer = SystemLogWriter(
            self.universe,
            filename=(log_path.split("/")[-1] if log_path else "sessions.jsonl"),
            max_mb=5.0,
            base_dir=None,
        )
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
        while self.running:
            try:
                self._snapshot()
            except Exception as exc:
                await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="warning", message=f"Session log error: {exc}"))
            await asyncio.sleep(self.interval_minutes * 60)

    def _snapshot(self):
        if not self.broker:
            return
        try:
            account = self.broker.get_account()
            positions = self.broker.get_positions()
        except Exception as exc:
            raise exc

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "universe": self.universe.value,
            "replay_enabled": getattr(config, "SIM_REPLAY_ENABLED", False),
            "portfolio_value": float(getattr(account, "portfolio_value", 0) or 0),
            "cash": float(getattr(account, "cash", 0) or 0),
            "buying_power": float(getattr(account, "buying_power", 0) or 0),
            "positions": [
                {
                    "symbol": getattr(p, "symbol", ""),
                    "qty": float(getattr(p, "qty", 0) or 0),
                    "avg_entry_price": float(getattr(p, "avg_entry_price", 0) or 0),
                    "market_value": float(getattr(p, "market_value", 0) or 0),
                    "unrealized_pl": float(getattr(p, "unrealized_pl", 0) or 0),
                }
                for p in positions
            ],
        }
        self._log_writer.write(entry)
