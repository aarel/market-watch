import os
import tempfile
import unittest
from unittest.mock import patch

from agents.event_bus import EventBus
from agents.ui_check_agent import UICheckAgent
from agents.events import LogEvent
from universe import Universe, UniverseContext


class TestUICheckAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)

    async def asyncTearDown(self):
        os.chdir(self.original_cwd)
        self.tmpdir.cleanup()

    async def test_emits_warning_on_failure(self):
        bus = EventBus(UniverseContext(Universe.PAPER))
        agent = UICheckAgent(bus, interval_minutes=30, url="http://localhost:9999")

        with patch("agents.ui_check_agent.requests.get", side_effect=Exception("boom")):
            await agent._check_once()

        events = bus.get_recent_events(1)
        self.assertTrue(events)
        event = events[-1]
        self.assertIsInstance(event, LogEvent)
        self.assertEqual(event.level, "warning")
        self.assertIn("UI check error", event.message)


if __name__ == "__main__":
    unittest.main()
