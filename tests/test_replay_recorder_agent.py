import os
import tempfile
import unittest
from datetime import datetime, timezone

import pandas as pd

from agents.event_bus import EventBus
from agents.replay_recorder_agent import ReplayRecorderAgent
from universe import Universe, UniverseContext, get_data_path


class DummyBroker:
    def __init__(self, bars):
        self._bars = bars

    def get_bars(self, symbol, days=2):
        return self._bars


class TestReplayRecorderAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

    async def asyncTearDown(self):
        os.chdir(self.original_cwd)
        self.tmpdir.cleanup()

    async def test_capture_once_writes_csv(self):
        now = datetime.now(timezone.utc)
        bars = pd.DataFrame(
            {
                "open": [1.0],
                "high": [1.1],
                "low": [0.9],
                "close": [1.0],
                "volume": [100],
            },
            index=[pd.Timestamp(now)],
        )
        broker = DummyBroker(bars)
        bus = EventBus(UniverseContext(Universe.PAPER))
        agent = ReplayRecorderAgent(bus, broker, interval_minutes=5, symbols=["TEST"])

        await agent._capture_once()

        today = now.date()
        out_path = os.path.join(
            get_data_path(Universe.PAPER, "replay"),
            f"TEST-{today.strftime('%Y%m%d')}.csv",
        )
        self.assertTrue(os.path.exists(out_path))


if __name__ == "__main__":
    unittest.main()
