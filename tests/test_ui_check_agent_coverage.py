import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agents.ui_check_agent import UICheckAgent
from universe import Universe, UniverseContext


class DummyBus:
    def __init__(self, context):
        self._context = context
        self.publish = AsyncMock()


class TestUICheckAgentCoverage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = DummyBus(self.context)

    def test_init_defaults_and_log_path(self):
        with patch("agents.ui_check_agent.SystemLogWriter") as mock_writer:
            with patch("agents.ui_check_agent.config.API_HOST", "localhost"), \
                patch("agents.ui_check_agent.config.UI_PORT", 8000):
                agent = UICheckAgent(self.bus, interval_minutes=1, log_path="logs/ui.jsonl")

        self.assertEqual(agent.interval_minutes, 5)
        self.assertEqual(agent.url, "http://localhost:8000")
        mock_writer.assert_called_once()

    async def test_check_once_ok(self):
        mock_resp = SimpleNamespace(
            status_code=200,
            text="metric-return position-pie-chart analytics-trades",
        )

        async def fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch("agents.ui_check_agent.SystemLogWriter") as mock_writer_cls:
            mock_writer = Mock()
            mock_writer_cls.return_value = mock_writer
            agent = UICheckAgent(self.bus, url="http://example.com")

            with patch("agents.ui_check_agent.asyncio.to_thread", new=fake_to_thread):
                with patch("agents.ui_check_agent.requests.get", return_value=mock_resp):
                    await agent._check_once()

        mock_writer.write.assert_called_once()
        event = self.bus.publish.await_args.args[0]
        self.assertEqual(event.level, "info")

    async def test_check_once_warn(self):
        mock_resp = SimpleNamespace(status_code=200, text="metric-return")

        async def fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch("agents.ui_check_agent.SystemLogWriter") as mock_writer_cls:
            mock_writer = Mock()
            mock_writer_cls.return_value = mock_writer
            agent = UICheckAgent(self.bus, url="http://example.com")

            with patch("agents.ui_check_agent.asyncio.to_thread", new=fake_to_thread):
                with patch("agents.ui_check_agent.requests.get", return_value=mock_resp):
                    await agent._check_once()

        event = self.bus.publish.await_args.args[0]
        self.assertEqual(event.level, "warning")

    async def test_check_once_error(self):
        async def fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch("agents.ui_check_agent.SystemLogWriter") as mock_writer_cls:
            mock_writer = Mock()
            mock_writer_cls.return_value = mock_writer
            agent = UICheckAgent(self.bus, url="http://example.com")

            with patch("agents.ui_check_agent.asyncio.to_thread", new=fake_to_thread):
                with patch("agents.ui_check_agent.requests.get", side_effect=Exception("boom")):
                    await agent._check_once()

        event = self.bus.publish.await_args.args[0]
        self.assertEqual(event.level, "warning")

    async def test_start_stop_cancels_task(self):
        async def long_loop(self):
            await asyncio.sleep(10)

        with patch.object(UICheckAgent, "_loop", new=long_loop):
            agent = UICheckAgent(self.bus, url="http://example.com")
            await agent.start()
            self.assertIsNotNone(agent._task)
            await agent.stop()
            self.assertFalse(agent.running)

    async def test_loop_publishes_on_exception(self):
        agent = UICheckAgent(self.bus, url="http://example.com")
        agent.running = True

        async def fake_sleep(_seconds):
            # Stop after second sleep (initial + loop)
            if getattr(fake_sleep, "calls", 0) == 0:
                fake_sleep.calls = 1
            else:
                agent.running = False

        with patch("agents.ui_check_agent.asyncio.sleep", new=fake_sleep):
            with patch.object(agent, "_check_once", side_effect=Exception("boom")):
                await agent._loop()

        self.bus.publish.assert_awaited()


if __name__ == "__main__":
    unittest.main()
