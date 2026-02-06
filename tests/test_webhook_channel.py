"""Tests for webhook alert channel."""
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from alerts.channels.webhook import WebhookChannel, WebhookType
from alerts.models import Alert, AlertTrigger, AlertSeverity, ChannelType


class TestWebhookChannel(unittest.IsolatedAsyncioTestCase):
    """Test webhook channel functionality."""

    def setUp(self):
        """Create webhook channel for testing."""
        self.channel = WebhookChannel(
            webhook_url="https://example.com/webhook",
            webhook_type=WebhookType.GENERIC,
            retry_attempts=3,
            timeout_seconds=10,
        )

    def test_validate_config_valid(self):
        """Test validation passes for valid config."""
        config = {
            "webhook_url": "https://example.com/webhook",
            "webhook_type": "generic",
        }

        result = self.channel.validate_config(config)
        self.assertTrue(result)

    def test_validate_config_missing_url(self):
        """Test validation fails for missing webhook_url."""
        config = {}

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("webhook_url", str(cm.exception))

    def test_validate_config_invalid_url(self):
        """Test validation fails for invalid URL format."""
        config = {
            "webhook_url": "not-a-url",
        }

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("http", str(cm.exception).lower())

    def test_validate_config_invalid_type(self):
        """Test validation fails for invalid webhook_type."""
        config = {
            "webhook_url": "https://example.com/webhook",
            "webhook_type": "invalid_type",
        }

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("webhook_type", str(cm.exception))

    @patch("aiohttp.ClientSession")
    async def test_send_success(self, mock_session_class):
        """Test successful webhook send."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.WEBHOOK],
        )

        result = await self.channel.send(alert)

        self.assertTrue(result)
        mock_session.post.assert_called_once()

    @patch("aiohttp.ClientSession")
    async def test_send_with_retry(self, mock_session_class):
        """Test webhook send retries on failure."""
        # Mock HTTP response to fail first time, succeed second time
        success_response = MagicMock()
        success_response.raise_for_status = MagicMock()
        success_response.__aenter__ = AsyncMock(return_value=success_response)
        success_response.__aexit__ = AsyncMock(return_value=None)

        fail_response = MagicMock()
        fail_response.raise_for_status = MagicMock(side_effect=Exception("Connection error"))
        fail_response.__aenter__ = AsyncMock(return_value=fail_response)
        fail_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=[fail_response, success_response])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.WEBHOOK],
        )

        result = await self.channel.send(alert)

        self.assertTrue(result)
        # Should have attempted twice
        self.assertEqual(mock_session.post.call_count, 2)

    @patch("aiohttp.ClientSession")
    async def test_send_all_retries_fail(self, mock_session_class):
        """Test webhook send fails after all retries."""
        # Mock HTTP response to always fail
        fail_response = MagicMock()
        fail_response.raise_for_status = MagicMock(side_effect=Exception("Connection error"))
        fail_response.__aenter__ = AsyncMock(return_value=fail_response)
        fail_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=fail_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.WEBHOOK],
        )

        with self.assertRaises(Exception) as cm:
            await self.channel.send(alert)

        self.assertIn("Connection error", str(cm.exception))
        # Should have attempted 3 times (retry_attempts)
        self.assertEqual(mock_session.post.call_count, 3)

    def test_format_generic(self):
        """Test generic payload formatting."""
        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.WEBHOOK],
        )

        payload = self.channel._format_generic(alert)

        self.assertEqual(payload["id"], "test1")
        self.assertEqual(payload["title"], "Test Alert")
        self.assertEqual(payload["severity"], "high")
        self.assertEqual(payload["context"], {"key": "value"})

    def test_format_discord(self):
        """Test Discord payload formatting."""
        channel = WebhookChannel(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type=WebhookType.DISCORD,
        )

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.WEBHOOK],
        )

        payload = channel._format_discord(alert)

        self.assertIn("embeds", payload)
        self.assertEqual(len(payload["embeds"]), 1)
        embed = payload["embeds"][0]
        self.assertIn("[HIGH] Test Alert", embed["title"])
        self.assertEqual(embed["description"], "This is a test alert")
        self.assertEqual(embed["color"], 0xfd7e14)  # Orange for HIGH
        self.assertTrue(any(f["name"] == "Trigger" for f in embed["fields"]))

    def test_format_slack(self):
        """Test Slack payload formatting."""
        channel = WebhookChannel(
            webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
            webhook_type=WebhookType.SLACK,
        )

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.WEBHOOK],
        )

        payload = channel._format_slack(alert)

        self.assertIn("attachments", payload)
        self.assertEqual(len(payload["attachments"]), 1)
        attachment = payload["attachments"][0]
        self.assertIn("[HIGH] Test Alert", attachment["title"])
        self.assertEqual(attachment["text"], "This is a test alert")
        self.assertEqual(attachment["color"], "danger")  # Red for HIGH
        self.assertTrue(any(f["title"] == "Trigger" for f in attachment["fields"]))

    def test_format_telegram(self):
        """Test Telegram payload formatting."""
        channel = WebhookChannel(
            webhook_url="https://api.telegram.org/bot123:ABC/sendMessage",
            webhook_type=WebhookType.TELEGRAM,
        )

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.WEBHOOK],
        )

        payload = channel._format_telegram(alert)

        self.assertIn("text", payload)
        self.assertEqual(payload["parse_mode"], "Markdown")
        text = payload["text"]
        self.assertIn("[HIGH] Test Alert", text)
        self.assertIn("This is a test alert", text)
        self.assertIn("anomaly_detected", text)
        self.assertIn("key", text)
        self.assertIn("value", text)

    def test_format_severity_colors_discord(self):
        """Test Discord uses correct colors for different severities."""
        channel = WebhookChannel(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type=WebhookType.DISCORD,
        )

        severities = [
            (AlertSeverity.LOW, 0x28a745),
            (AlertSeverity.MEDIUM, 0xffc107),
            (AlertSeverity.HIGH, 0xfd7e14),
            (AlertSeverity.CRITICAL, 0xdc3545),
        ]

        for severity, expected_color in severities:
            alert = Alert(
                id="test1",
                rule_id="rule1",
                timestamp=datetime.now(),
                trigger=AlertTrigger.ANOMALY_DETECTED,
                severity=severity,
                title="Test Alert",
                message="Test message",
                channels=[ChannelType.WEBHOOK],
            )

            payload = channel._format_discord(alert)
            self.assertEqual(payload["embeds"][0]["color"], expected_color)

    def test_get_name(self):
        """Test channel name includes webhook type."""
        generic_channel = WebhookChannel(
            webhook_url="https://example.com/webhook",
            webhook_type=WebhookType.GENERIC,
        )
        self.assertEqual(generic_channel.get_name(), "Webhook (generic)")

        discord_channel = WebhookChannel(
            webhook_url="https://discord.com/api/webhooks/123/abc",
            webhook_type=WebhookType.DISCORD,
        )
        self.assertEqual(discord_channel.get_name(), "Webhook (discord)")


if __name__ == "__main__":
    unittest.main()
