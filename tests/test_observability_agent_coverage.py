import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agents.event_bus import EventBus
from agents.events import MarketDataReady
from agents.observability_agent import ObservabilityAgent
from universe import Universe, UniverseContext


class TestObservabilityAgentCoverage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(context)

    async def test_start_stop_unsubscribes(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")
        await agent.start()
        self.assertIn(agent._handle_event, self.bus._global_subscribers)

        await agent.stop()
        self.assertNotIn(agent._handle_event, self.bus._global_subscribers)
        self.assertFalse(agent.running)

    async def test_handle_event_logs_error_on_exception(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")
        event = MarketDataReady(universe=self.bus._context.universe, session_id=self.bus._context.session_id)

        with patch("agents.observability_agent.classify_event", side_effect=Exception("boom")):
            with patch("agents.observability_agent.logger") as mocked_logger:
                await agent._handle_event(event)
                mocked_logger.error.assert_called()

    def test_baseline_init_returns_when_already_initialized(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")
        agent._baseline_initialized = True

        detector = Mock()
        agent._maybe_initialize_baseline(detector)
        detector.update_baseline.assert_not_called()

    def test_baseline_init_sets_flag_when_rate_present(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")

        detector = Mock()
        detector.get_status.return_value = {
            "warn_events": {"baseline_rate": 0.1},
            "fail_events": {"baseline_rate": None},
        }

        agent._maybe_initialize_baseline(detector)
        self.assertTrue(agent._baseline_initialized)

    async def test_anomaly_alert_respects_cooldown(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")
        agent._last_anomaly_alert_at = datetime.now()

        detector = Mock()
        detector.detect_anomaly.return_value = {"severity": "high"}

        with patch("agents.observability_agent.get_manager") as mocked_get_manager:
            await agent._maybe_alert_on_anomaly(detector, datetime.now())
            mocked_get_manager.assert_not_called()

    async def test_anomaly_alert_triggers_and_updates_timestamp(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")

        detector = Mock()
        detector.detect_anomaly.return_value = {
            "type": "fail_spike",
            "current_rate": 5.0,
            "baseline_rate": 1.0,
            "multiplier": 5.0,
            "severity": "high",
            "message": "Failure event rate spike",
            "event_count": 12,
        }

        manager = SimpleNamespace(trigger_alert=AsyncMock())
        with patch("agents.observability_agent.get_manager", return_value=manager):
            await agent._maybe_alert_on_anomaly(detector, datetime.now())

        manager.trigger_alert.assert_awaited()
        self.assertIsNotNone(agent._last_anomaly_alert_at)

    async def test_anomaly_alert_logs_error_on_failure(self):
        agent = ObservabilityAgent(self.bus, log_path="observability.jsonl")

        detector = Mock()
        detector.detect_anomaly.return_value = {"severity": "medium"}

        manager = SimpleNamespace(trigger_alert=AsyncMock(side_effect=Exception("alert failure")))
        with patch("agents.observability_agent.get_manager", return_value=manager):
            with patch("agents.observability_agent.logger") as mocked_logger:
                await agent._maybe_alert_on_anomaly(detector, datetime.now())
                mocked_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
