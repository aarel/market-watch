"""Tests for email alert channel."""
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from alerts.channels.email import EmailChannel
from alerts.models import Alert, AlertSeverity, AlertTrigger, ChannelType


class TestEmailChannel(unittest.IsolatedAsyncioTestCase):
    """Test email channel functionality."""

    def setUp(self):
        """Create email channel for testing."""
        self.channel = EmailChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="test@example.com",
            smtp_password="password",
            from_addr="alerts@example.com",
            to_addrs=["user@example.com"],
            use_tls=True,
            retry_attempts=3,
        )

    def test_validate_config_valid(self):
        """Test validation passes for valid config."""
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "password",
            "from_addr": "alerts@example.com",
            "to_addrs": ["user@example.com"],
        }

        result = self.channel.validate_config(config)
        self.assertTrue(result)

    def test_validate_config_missing_field(self):
        """Test validation fails for missing required field."""
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            # Missing smtp_user
            "smtp_password": "password",
            "from_addr": "alerts@example.com",
            "to_addrs": ["user@example.com"],
        }

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("smtp_user", str(cm.exception))

    def test_validate_config_empty_recipients(self):
        """Test validation fails for empty recipient list."""
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "password",
            "from_addr": "alerts@example.com",
            "to_addrs": [],  # Empty list
        }

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("to_addrs", str(cm.exception))

    def test_validate_config_invalid_port(self):
        """Test validation fails for non-integer port."""
        config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": "587",  # String instead of int
            "smtp_user": "test@example.com",
            "smtp_password": "password",
            "from_addr": "alerts@example.com",
            "to_addrs": ["user@example.com"],
        }

        with self.assertRaises(ValueError) as cm:
            self.channel.validate_config(config)

        self.assertIn("smtp_port", str(cm.exception))

    @patch("smtplib.SMTP")
    async def test_send_success(self, mock_smtp_class):
        """Test successful email send."""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.EMAIL],
        )

        result = await self.channel.send(alert)

        self.assertTrue(result)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()

    @patch("smtplib.SMTP")
    async def test_send_with_retry(self, mock_smtp_class):
        """Test email send retries on failure."""
        # Mock SMTP server to fail first time, succeed second time
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        mock_server.send_message.side_effect = [
            Exception("Connection error"),  # First attempt fails
            None,  # Second attempt succeeds
        ]

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.EMAIL],
        )

        result = await self.channel.send(alert)

        self.assertTrue(result)
        # Should have attempted twice
        self.assertEqual(mock_server.send_message.call_count, 2)

    @patch("smtplib.SMTP")
    async def test_send_all_retries_fail(self, mock_smtp_class):
        """Test email send fails after all retries."""
        # Mock SMTP server to always fail
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        mock_server.send_message.side_effect = Exception("Connection error")

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.EMAIL],
        )

        with self.assertRaises(Exception) as cm:
            await self.channel.send(alert)

        self.assertIn("Connection error", str(cm.exception))
        # Should have attempted 3 times (retry_attempts)
        self.assertEqual(mock_server.send_message.call_count, 3)

    @patch("smtplib.SMTP_SSL")
    async def test_send_without_tls(self, mock_smtp_ssl_class):
        """Test email send using SSL instead of TLS."""
        # Create channel without TLS
        channel = EmailChannel(
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_user="test@example.com",
            smtp_password="password",
            from_addr="alerts@example.com",
            to_addrs=["user@example.com"],
            use_tls=False,  # Use SSL
        )

        # Mock SMTP_SSL server
        mock_server = MagicMock()
        mock_smtp_ssl_class.return_value.__enter__.return_value = mock_server

        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime.now(),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            channels=[ChannelType.EMAIL],
        )

        result = await channel.send(alert)

        self.assertTrue(result)
        # Should use SMTP_SSL, not call starttls
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()

    def test_format_text(self):
        """Test plain text formatting."""
        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.EMAIL],
        )

        text = self.channel._format_text(alert)

        self.assertIn("Test Alert", text)
        self.assertIn("HIGH", text)
        self.assertIn("anomaly_detected", text)
        self.assertIn("This is a test alert", text)
        self.assertIn("key: value", text)

    def test_format_html(self):
        """Test HTML formatting."""
        alert = Alert(
            id="test1",
            rule_id="rule1",
            timestamp=datetime(2026, 2, 5, 12, 0, 0),
            trigger=AlertTrigger.ANOMALY_DETECTED,
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            context={"key": "value"},
            channels=[ChannelType.EMAIL],
        )

        html = self.channel._format_html(alert)

        self.assertIn("Test Alert", html)
        self.assertIn("HIGH", html)
        self.assertIn("anomaly_detected", html)
        self.assertIn("This is a test alert", html)
        self.assertIn("key", html)
        self.assertIn("value", html)
        # Should have HTML structure
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("</html>", html)

    def test_format_html_severity_colors(self):
        """Test HTML uses correct colors for different severities."""
        severities = [
            (AlertSeverity.LOW, "#28a745"),
            (AlertSeverity.MEDIUM, "#ffc107"),
            (AlertSeverity.HIGH, "#fd7e14"),
            (AlertSeverity.CRITICAL, "#dc3545"),
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
                channels=[ChannelType.EMAIL],
            )

            html = self.channel._format_html(alert)
            self.assertIn(expected_color, html)

    def test_get_name(self):
        """Test channel name."""
        self.assertEqual(self.channel.get_name(), "Email")


if __name__ == "__main__":
    unittest.main()
