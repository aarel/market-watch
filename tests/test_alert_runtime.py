import unittest
from datetime import datetime, timezone

import config
from alerts.manager import get_manager
from alerts.models import AlertRule, AlertTrigger, AlertSeverity, ChannelType
from alerts.channels.base import AlertChannel
from alerts.runtime import configure_alerts
from agents.event_bus import EventBus
from agents.external_alert_agent import ExternalAlertAgent
from agents.events import OrderFailed, RiskCheckFailed, LogEvent
from universe import Universe, UniverseContext


class MockChannel(AlertChannel):
    """Mock channel for runtime wiring tests."""

    def __init__(self):
        self.sent_alerts = []

    async def send(self, alert):
        self.sent_alerts.append(alert)
        return True

    def validate_config(self, config):  # pragma: no cover
        return True

    def get_name(self) -> str:  # pragma: no cover
        return "MockChannel"


def _reset_manager():
    manager = get_manager()
    manager._rules.clear()
    manager._channels.clear()
    manager._history.clear()
    return manager


class TestAlertRuntimeConfig(unittest.TestCase):
    def setUp(self):
        self.manager = _reset_manager()
        self.original = {
            "ALERTS_ENABLED": config.ALERTS_ENABLED,
            "ALERT_EMAIL_ENABLED": config.ALERT_EMAIL_ENABLED,
            "ALERT_WEBHOOK_ENABLED": config.ALERT_WEBHOOK_ENABLED,
            "ALERT_WEBHOOK_URL": config.ALERT_WEBHOOK_URL,
        }

    def tearDown(self):
        for key, value in self.original.items():
            setattr(config, key, value)
        _reset_manager()

    def test_configure_alerts_registers_default_rules(self):
        config.ALERTS_ENABLED = True
        config.ALERT_WEBHOOK_ENABLED = True
        config.ALERT_WEBHOOK_URL = "http://example.com"

        summary = configure_alerts({
            "alerts_enabled": True,
            "alert_email_enabled": False,
            "alert_webhook_enabled": True,
        })

        self.assertIn("webhook", summary["channels"])
        triggers = {rule.trigger for rule in self.manager.list_rules()}
        self.assertIn(AlertTrigger.ANOMALY_DETECTED, triggers)
        self.assertIn(AlertTrigger.ORDER_FAILED, triggers)
        self.assertIn(AlertTrigger.SYSTEM_ERROR, triggers)
        self.assertIn(AlertTrigger.DAILY_LOSS_LIMIT, triggers)
        self.assertIn(AlertTrigger.MAX_DRAWDOWN, triggers)


class TestExternalAlertAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = _reset_manager()
        self.channel = MockChannel()
        self.manager.register_channel(ChannelType.EMAIL, self.channel)
        self.context = UniverseContext(Universe.SIMULATION)
        self.event_bus = EventBus(self.context)
        self.agent = ExternalAlertAgent(self.event_bus, cooldown_seconds=60)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()
        _reset_manager()

    async def test_order_failed_triggers_alert(self):
        self.manager.add_rule(AlertRule(
            id="order_failed",
            name="Order Failed",
            trigger=AlertTrigger.ORDER_FAILED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        ))

        event = OrderFailed(
            universe=self.context.universe,
            session_id=self.context.session_id,
            source="ExecutionAgent",
            symbol="AAPL",
            action="buy",
            reason="Broker error",
        )
        await self.event_bus.publish(event)

        self.assertEqual(len(self.channel.sent_alerts), 1)
        self.assertEqual(self.channel.sent_alerts[0].trigger, AlertTrigger.ORDER_FAILED)

    async def test_circuit_breaker_daily_loss_triggers_alert(self):
        self.manager.add_rule(AlertRule(
            id="daily_loss",
            name="Daily Loss",
            trigger=AlertTrigger.DAILY_LOSS_LIMIT,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        ))

        event = RiskCheckFailed(
            universe=self.context.universe,
            session_id=self.context.session_id,
            source="RiskAgent",
            symbol="TSLA",
            action="buy",
            reason="Circuit breaker active: Daily loss limit hit (test)",
        )
        await self.event_bus.publish(event)

        self.assertEqual(len(self.channel.sent_alerts), 1)
        self.assertEqual(self.channel.sent_alerts[0].trigger, AlertTrigger.DAILY_LOSS_LIMIT)

    async def test_system_error_triggers_alert(self):
        self.manager.add_rule(AlertRule(
            id="system_error",
            name="System Error",
            trigger=AlertTrigger.SYSTEM_ERROR,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        ))

        event = LogEvent(
            universe=self.context.universe,
            session_id=self.context.session_id,
            source="Coordinator",
            level="error",
            message="Unhandled exception",
            timestamp=datetime.now(timezone.utc),
        )
        await self.event_bus.publish(event)

        self.assertEqual(len(self.channel.sent_alerts), 1)
        self.assertEqual(self.channel.sent_alerts[0].trigger, AlertTrigger.SYSTEM_ERROR)


if __name__ == "__main__":
    unittest.main()
