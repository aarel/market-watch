import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agents.event_bus import EventBus
from agents.events import LogEvent, OrderFailed, RiskCheckFailed
from agents.external_alert_agent import ExternalAlertAgent
from universe import Universe, UniverseContext


class TestExternalAlertAgentCoverage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(context)

    async def test_risk_failed_non_circuit_breaker_ignored(self):
        agent = ExternalAlertAgent(self.bus)
        event = RiskCheckFailed(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="RiskAgent",
            symbol="AAA",
            action="buy",
            reason="Some other failure",
            timestamp=datetime.now(UTC),
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_risk_failed(event)
            mocked_send.assert_not_awaited()

    async def test_risk_failed_daily_loss_triggers_critical(self):
        agent = ExternalAlertAgent(self.bus)
        event = RiskCheckFailed(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="RiskAgent",
            symbol="AAA",
            action="buy",
            reason="Circuit breaker active: Daily loss limit hit",
            timestamp=datetime.now(UTC),
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_risk_failed(event)
            mocked_send.assert_awaited()
            args = mocked_send.await_args
            self.assertEqual(args.args[0].value, "daily_loss_limit")
            self.assertEqual(args.args[1].value, "critical")

    async def test_risk_failed_max_drawdown_triggers_critical(self):
        agent = ExternalAlertAgent(self.bus)
        event = RiskCheckFailed(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="RiskAgent",
            symbol="AAA",
            action="buy",
            reason="Circuit breaker active: Max drawdown limit hit",
            timestamp=datetime.now(UTC),
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_risk_failed(event)
            mocked_send.assert_awaited()
            args = mocked_send.await_args
            self.assertEqual(args.args[0].value, "max_drawdown")
            self.assertEqual(args.args[1].value, "critical")

    async def test_risk_failed_respects_cooldown(self):
        agent = ExternalAlertAgent(self.bus, cooldown_seconds=60)
        now = datetime.now(UTC)
        event = RiskCheckFailed(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="RiskAgent",
            symbol="AAA",
            action="buy",
            reason="Circuit breaker active: Daily loss limit hit",
            timestamp=now,
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_risk_failed(event)
            followup = RiskCheckFailed(
                universe=self.bus._context.universe,
                session_id=self.bus._context.session_id,
                source="RiskAgent",
                symbol="AAA",
                action="buy",
                reason="Circuit breaker active: Daily loss limit hit",
                timestamp=now + timedelta(seconds=30),
            )
            await agent._handle_risk_failed(followup)
            self.assertEqual(mocked_send.await_count, 1)

    async def test_order_failed_respects_cooldown(self):
        agent = ExternalAlertAgent(self.bus, cooldown_seconds=60)
        now = datetime.now(UTC)
        event = OrderFailed(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="ExecutionAgent",
            symbol="AAA",
            action="buy",
            reason="Order failed",
            timestamp=now,
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_order_failed(event)
            await agent._handle_order_failed(event)
            self.assertEqual(mocked_send.await_count, 1)

    async def test_log_event_ignores_non_error_levels(self):
        agent = ExternalAlertAgent(self.bus)
        event = LogEvent(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="System",
            level="info",
            message="All good",
            timestamp=datetime.now(UTC),
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_log_event(event)
            mocked_send.assert_not_awaited()

    async def test_log_event_critical_level_sends_alert(self):
        agent = ExternalAlertAgent(self.bus)
        event = LogEvent(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="System",
            level="critical",
            message="Disk failure",
            timestamp=datetime.now(UTC),
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_log_event(event)
            mocked_send.assert_awaited()

    async def test_log_event_respects_cooldown(self):
        agent = ExternalAlertAgent(self.bus, cooldown_seconds=60)
        now = datetime.now(UTC)
        event = LogEvent(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="System",
            level="error",
            message="Disk failure",
            timestamp=now,
        )

        with patch.object(agent, "_send_alert", new=AsyncMock()) as mocked_send:
            await agent._handle_log_event(event)
            followup = LogEvent(
                universe=self.bus._context.universe,
                session_id=self.bus._context.session_id,
                source="System",
                level="error",
                message="Disk failure",
                timestamp=now + timedelta(seconds=30),
            )
            await agent._handle_log_event(followup)
            self.assertEqual(mocked_send.await_count, 1)

    async def test_send_alert_logs_error_on_exception(self):
        agent = ExternalAlertAgent(self.bus)
        manager = SimpleNamespace(trigger_alert=AsyncMock(side_effect=Exception("alert error")))

        with patch("agents.external_alert_agent.get_manager", return_value=manager):
            with patch("agents.external_alert_agent.logger") as mocked_logger:
                await agent._send_alert(
                    trigger=SimpleNamespace(value="system_error"),
                    severity=SimpleNamespace(value="high"),
                    title="title",
                    message="msg",
                    context={},
                )
                mocked_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
