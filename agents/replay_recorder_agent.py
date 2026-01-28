"""ReplayRecorderAgent - captures intraday bars for SIM replay."""
import asyncio
import csv
import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict

import config
from .base import BaseAgent
from .events import LogEvent


class ReplayRecorderAgent(BaseAgent):
    """Periodically records latest bars to data/replay for later SIM replay."""

    def __init__(self, event_bus, broker, interval_minutes: int = 5, symbols: Optional[list[str]] = None):
        super().__init__("ReplayRecorderAgent", event_bus)
        self.broker = broker
        self.interval_minutes = max(1, interval_minutes)
        self.symbols = symbols or config.WATCHLIST
        self._task: Optional[asyncio.Task] = None
        self._last_ts: Dict[str, datetime] = {}

    async def start(self):
        await super().start()
        # Small delay to let other agents boot
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
                await self._capture_once()
            except Exception as exc:
                await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="warning", message=f"ReplayRecorder error: {exc}"))
            await asyncio.sleep(self.interval_minutes * 60)

    async def _capture_once(self):
        # Record only when not in SIM mode; expect real broker data
        from universe import Universe
        if self.universe == Universe.SIMULATION:
            return
        today = datetime.utcnow().date()
        out_dir = config.REPLAY_RECORDER_DIR
        os.makedirs(out_dir, exist_ok=True)
        symbols = self.symbols or []
        if not symbols:
            return
        for sym in symbols:
            try:
                bars = self.broker.get_bars(sym, days=2)
                if bars is None or len(bars) == 0:
                    continue
                # Use most recent bar
                ts = bars.index[-1].to_pydatetime()
                if ts.date() != today:
                    continue
                last_seen = self._last_ts.get(sym)
                if last_seen and ts <= last_seen:
                    continue
                row = bars.iloc[-1]
                out_path = os.path.join(out_dir, f"{sym}-{today.strftime('%Y%m%d')}.csv")
                write_header = not os.path.exists(out_path)
                with open(out_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if write_header:
                        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
                    writer.writerow([
                        ts.isoformat(),
                        float(row["open"]),
                        float(row["high"]),
                        float(row["low"]),
                        float(row["close"]),
                        int(row["volume"]),
                    ])
                self._last_ts[sym] = ts
            except Exception as exc:
                await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="warning", message=f"ReplayRecorder {sym} failed: {exc}"))
