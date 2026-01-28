"""TestAgent - runs automated test suite on a schedule."""
import asyncio
import json
import os
import subprocess
from datetime import datetime
from typing import Optional

from .base import BaseAgent
from .events import LogEvent
import config
from monitoring.logger import SystemLogWriter
from universe import Universe


class TestAgent(BaseAgent):
    """Periodically runs the test suite and logs results."""

    def __init__(self, event_bus, interval_minutes: int, log_path: Optional[str] = None):
        super().__init__("TestAgent", event_bus)
        self.interval_minutes = max(5, interval_minutes)
        filename = (log_path.split("/")[-1] if log_path else "tests.jsonl")
        self._log_writer = SystemLogWriter(self.universe, filename=filename)
        self._task: Optional[asyncio.Task] = None

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
        # small initial delay to avoid startup storm
        await asyncio.sleep(5)
        while self.running:
            await self._run_tests_once()
            await asyncio.sleep(self.interval_minutes * 60)

    async def _run_tests_once(self):
        cmd = ["bash", "scripts/run_tests.sh"]
        started = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.interval_minutes * 60,  # don't hang longer than interval
            )
            duration = (datetime.now() - started).total_seconds()
            entry = {
                "timestamp": datetime.now().isoformat(),
                "command": " ".join(cmd),
                "exit_code": result.returncode,
                "duration_sec": duration,
                "stdout_tail": result.stdout.splitlines()[-20:],
                "stderr_tail": result.stderr.splitlines()[-20:],
            }
            self._log_writer.write(entry)
            level = "info" if result.returncode == 0 else "warning"
            msg = f"TestAgent run exit={result.returncode} duration={duration:.1f}s"
            await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level=level, message=msg))
        except subprocess.TimeoutExpired:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "command": " ".join(cmd),
                "exit_code": -1,
                "duration_sec": (datetime.now() - started).total_seconds(),
                "error": "timeout",
            }
            self._log_writer.write(entry)
            await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="warning", message="TestAgent run timed out"))
        except Exception as exc:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "command": " ".join(cmd),
                "exit_code": -1,
                "duration_sec": (datetime.now() - started).total_seconds(),
                "error": str(exc),
            }
            self._log_writer.write(entry)
            await self.event_bus.publish(LogEvent(universe=self.universe, session_id=self.session_id, source=self.name, level="error", message=f"TestAgent error: {exc}"))
