"""Tests for alert framework."""
import unittest
import asyncio
from datetime import datetime
from alerts.models import AlertRule, Alert, AlertTrigger, AlertSeverity, ChannelType
from alerts.manager import AlertManager
from alerts.channels.base import AlertChannel


class MockChannel(AlertChannel):
    """Mock channel for testing."""

    def __init__(self, should_fail: bool = False):
        self.sent_alerts = []
        self.should_fail = should_fail

    async def send(self, alert: Alert) -> bool:
        """Mock send implementation."""
        if self.should_fail:
            raise Exception("Mock delivery failure")
        self.sent_alerts.append(alert)
        return True

    def validate_config(self, config) -> bool:
        """Mock validation."""
        return True

    def get_name(self) -> str:
        """Get channel name."""
        return "MockChannel"


class TestAlertModels(unittest.TestCase):
    """Test alert data models."""

    def test_alert_rule_matches_exact_severity(self):
        """Test rule matches when severity is exact."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.assertTrue(
            rule.matches(AlertTrigger.ANOMALY_DETECTED, AlertSeverity.MEDIUM)
        )

    def test_alert_rule_matches_higher_severity(self):
        """Test rule matches when event severity is higher."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.assertTrue(
            rule.matches(AlertTrigger.ANOMALY_DETECTED, AlertSeverity.HIGH)
        )
        self.assertTrue(
            rule.matches(AlertTrigger.ANOMALY_DETECTED, AlertSeverity.CRITICAL)
        )

    def test_alert_rule_no_match_lower_severity(self):
        """Test rule doesn't match when event severity is lower."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.assertFalse(
            rule.matches(AlertTrigger.ANOMALY_DETECTED, AlertSeverity.LOW)
        )

    def test_alert_rule_no_match_different_trigger(self):
        """Test rule doesn't match different trigger type."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.assertFalse(
            rule.matches(AlertTrigger.CIRCUIT_BREAKER, AlertSeverity.MEDIUM)
        )

    def test_alert_rule_disabled_no_match(self):
        """Test disabled rule doesn't match."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
            enabled=False,
        )

        self.assertFalse(
            rule.matches(AlertTrigger.ANOMALY_DETECTED, AlertSeverity.MEDIUM)
        )

    def test_alert_to_dict(self):
        """Test alert serialization to dict."""
        alert = Alert(
            id="alert1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.EMAIL],
        )

        result = alert.to_dict()

        self.assertEqual(result["id"], "alert1")
        self.assertEqual(result["rule_id"], "rule1")
        self.assertEqual(result["trigger"], "anomaly_detected")
        self.assertEqual(result["severity"], "high")
        self.assertEqual(result["title"], "Test Alert")
        self.assertEqual(result["context"], {"key": "value"})
        self.assertEqual(result["channels"], ["email"])


class TestAlertManager(unittest.IsolatedAsyncioTestCase):
    """Test alert manager functionality."""

    async def asyncSetUp(self):
        """Create fresh manager for each test."""
        self.manager = AlertManager()
        self.mock_channel = MockChannel()
        self.manager.register_channel(ChannelType.EMAIL, self.mock_channel)

    async def test_add_and_get_rule(self):
        """Test adding and retrieving a rule."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.manager.add_rule(rule)
        retrieved = self.manager.get_rule("test1")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, "test1")
        self.assertEqual(retrieved.name, "Test Rule")

    async def test_remove_rule(self):
        """Test removing a rule."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )

        self.manager.add_rule(rule)
        self.manager.remove_rule("test1")
        retrieved = self.manager.get_rule("test1")

        self.assertIsNone(retrieved)

    async def test_list_rules(self):
        """Test listing all rules."""
        rule1 = AlertRule(
            id="test1",
            name="Rule 1",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        rule2 = AlertRule(
            id="test2",
            name="Rule 2",
            trigger=AlertTrigger.CIRCUIT_BREAKER,
            severity=AlertSeverity.HIGH,
            channels=[ChannelType.WEBHOOK],
        )

        self.manager.add_rule(rule1)
        self.manager.add_rule(rule2)
        rules = self.manager.list_rules()

        self.assertEqual(len(rules), 2)

    async def test_trigger_alert_sends_to_channel(self):
        """Test triggering alert sends to registered channel."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        alerts = await self.manager.trigger_alert(
            trigger_type=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test message",
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(self.mock_channel.sent_alerts), 1)
        self.assertEqual(alerts[0].title, "Test Alert")

    async def test_trigger_alert_respects_severity(self):
        """Test alert only triggers for appropriate severity."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        # Should not trigger (severity too low)
        alerts = await self.manager.trigger_alert(
            trigger_type=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            title="Test Alert",
            message="Test message",
        )

        self.assertEqual(len(alerts), 0)
        self.assertEqual(len(self.mock_channel.sent_alerts), 0)

    async def test_trigger_alert_respects_trigger_type(self):
        """Test alert only triggers for matching trigger type."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        # Should not trigger (different trigger type)
        alerts = await self.manager.trigger_alert(
            trigger_type=AlertTrigger.CIRCUIT_BREAKER,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test message",
        )

        self.assertEqual(len(alerts), 0)
        self.assertEqual(len(self.mock_channel.sent_alerts), 0)

    async def test_trigger_alert_handles_channel_failure(self):
        """Test manager handles channel delivery failures."""
        failing_channel = MockChannel(should_fail=True)
        self.manager.register_channel(ChannelType.WEBHOOK, failing_channel)

        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.WEBHOOK],
        )
        self.manager.add_rule(rule)

        alerts = await self.manager.trigger_alert(
            trigger_type=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test message",
        )

        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].delivery_attempts, 1)
        self.assertTrue(len(alerts[0].delivery_errors) > 0)
        self.assertIn("Mock delivery failure", alerts[0].delivery_errors[0])

    async def test_get_history(self):
        """Test retrieving alert history."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        # Trigger 3 alerts
        for i in range(3):
            await self.manager.trigger_alert(
                trigger_type=AlertTrigger.ANOMALY_DETECTED,
                severity=AlertSeverity.HIGH,
                title=f"Alert {i}",
                message=f"Message {i}",
            )

        history = self.manager.get_history()

        self.assertEqual(len(history), 3)
        # Should be newest first
        self.assertEqual(history[0].title, "Alert 2")
        self.assertEqual(history[2].title, "Alert 0")

    async def test_get_history_with_limit(self):
        """Test retrieving limited alert history."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        # Trigger 5 alerts
        for i in range(5):
            await self.manager.trigger_alert(
                trigger_type=AlertTrigger.ANOMALY_DETECTED,
                severity=AlertSeverity.HIGH,
                title=f"Alert {i}",
                message=f"Message {i}",
            )

        history = self.manager.get_history(limit=2)

        self.assertEqual(len(history), 2)
        # Should get 2 newest
        self.assertEqual(history[0].title, "Alert 4")
        self.assertEqual(history[1].title, "Alert 3")

    async def test_clear_history(self):
        """Test clearing alert history."""
        rule = AlertRule(
            id="test1",
            name="Test Rule",
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.MEDIUM,
            channels=[ChannelType.EMAIL],
        )
        self.manager.add_rule(rule)

        await self.manager.trigger_alert(
            trigger_type=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="Test message",
        )

        self.manager.clear_history()
        history = self.manager.get_history()

        self.assertEqual(len(history), 0)


if __name__ == "__main__":
    unittest.main()
