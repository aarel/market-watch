"""Phase 7 alert tests: Telegram chat_id fix and JSONL persistence."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from alerts.channels.webhook import WebhookChannel, WebhookType
from alerts.manager import AlertManager
from alerts.models import Alert, AlertRule, AlertSeverity, AlertTrigger, ChannelType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(**kwargs) -> Alert:
    defaults = dict(
        id="test-id-1",
        rule_id="rule-1",
        timestamp=datetime(2026, 3, 8, 12, 0, 0),
        trigger=AlertTrigger.CUSTOM,
        severity=AlertSeverity.LOW,
        title="Test Alert",
        message="A test message",
        context={},
        channels=[ChannelType.WEBHOOK],
    )
    defaults.update(kwargs)
    return Alert(**defaults)


def _make_manager_with_rule(history_path=None) -> AlertManager:
    manager = AlertManager(max_history=10, history_path=history_path)
    rule = AlertRule(
        id="r1",
        name="Custom Rule",
        trigger=AlertTrigger.CUSTOM,
        severity=AlertSeverity.LOW,
        channels=[ChannelType.WEBHOOK],
        enabled=True,
    )
    manager.add_rule(rule)
    return manager


# ---------------------------------------------------------------------------
# Telegram chat_id fix
# ---------------------------------------------------------------------------

class TestTelegramChatId(unittest.TestCase):
    """WebhookChannel._format_telegram now includes chat_id when configured."""

    def _channel(self, chat_id=""):
        return WebhookChannel(
            webhook_url="https://api.telegram.org/botTOKEN/sendMessage",
            webhook_type=WebhookType.TELEGRAM,
            telegram_chat_id=chat_id,
        )

    def test_format_telegram_includes_chat_id_when_set(self):
        channel = self._channel(chat_id="123456789")
        alert = _make_alert()
        payload = channel._format_telegram(alert)
        self.assertIn("chat_id", payload)
        self.assertEqual(payload["chat_id"], "123456789")

    def test_format_telegram_omits_chat_id_when_empty(self):
        channel = self._channel(chat_id="")
        alert = _make_alert()
        payload = channel._format_telegram(alert)
        self.assertNotIn("chat_id", payload)

    def test_format_telegram_has_text(self):
        channel = self._channel(chat_id="abc")
        alert = _make_alert(title="Price Alert", severity=AlertSeverity.HIGH)
        payload = channel._format_telegram(alert)
        self.assertIn("text", payload)
        self.assertIn("Price Alert", payload["text"])

    def test_format_telegram_parse_mode_markdown(self):
        channel = self._channel(chat_id="xyz")
        alert = _make_alert()
        payload = channel._format_telegram(alert)
        self.assertEqual(payload.get("parse_mode"), "Markdown")

    def test_format_telegram_severity_in_text(self):
        channel = self._channel(chat_id="1")
        alert = _make_alert(severity=AlertSeverity.CRITICAL)
        payload = channel._format_telegram(alert)
        self.assertIn("CRITICAL", payload["text"])

    def test_format_telegram_context_in_text(self):
        channel = self._channel(chat_id="1")
        alert = _make_alert(context={"symbol": "AAPL", "loss": "-5%"})
        payload = channel._format_telegram(alert)
        self.assertIn("symbol", payload["text"])
        self.assertIn("AAPL", payload["text"])

    def test_channel_stores_telegram_chat_id(self):
        channel = self._channel(chat_id="my-chat")
        self.assertEqual(channel.telegram_chat_id, "my-chat")

    def test_channel_default_chat_id_is_empty(self):
        channel = WebhookChannel(
            webhook_url="https://example.com/hook",
            webhook_type=WebhookType.TELEGRAM,
        )
        self.assertEqual(channel.telegram_chat_id, "")

    def test_format_payload_routes_to_telegram(self):
        channel = self._channel(chat_id="999")
        alert = _make_alert()
        payload = channel._format_payload(alert)
        # Telegram payloads have text + parse_mode
        self.assertIn("text", payload)
        self.assertIn("parse_mode", payload)

    def test_non_telegram_webhook_has_no_chat_id(self):
        channel = WebhookChannel(
            webhook_url="https://discord.com/api/webhooks/x/y",
            webhook_type=WebhookType.DISCORD,
        )
        alert = _make_alert()
        payload = channel._format_payload(alert)
        self.assertNotIn("chat_id", payload)


# ---------------------------------------------------------------------------
# JSONL persistence — _persist_alert
# ---------------------------------------------------------------------------

class TestPersistAlert(unittest.TestCase):
    """Alert manager appends alerts to JSONL when history_path is set."""

    def test_persist_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            alert = _make_alert()
            manager._persist_alert(alert)
            self.assertTrue(path.exists())

    def test_persist_appends_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            alert = _make_alert(title="Foo")
            manager._persist_alert(alert)
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["title"], "Foo")

    def test_persist_appends_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            for i in range(3):
                manager._persist_alert(_make_alert(id=f"id-{i}", title=f"Alert{i}"))
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 3)

    def test_persist_no_op_when_no_path(self):
        manager = AlertManager()  # no history_path
        alert = _make_alert()
        # Must not raise
        manager._persist_alert(alert)

    def test_persist_creates_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "a" / "b" / "c" / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            manager._persist_alert(_make_alert())
            self.assertTrue(path.exists())

    def test_persist_json_has_expected_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            alert = _make_alert(
                id="abc",
                severity=AlertSeverity.HIGH,
                trigger=AlertTrigger.ANOMALY_DETECTED,
            )
            manager._persist_alert(alert)
            row = json.loads(path.read_text().strip())
            self.assertEqual(row["id"], "abc")
            self.assertEqual(row["severity"], "high")
            self.assertEqual(row["trigger"], "anomaly_detected")


# ---------------------------------------------------------------------------
# JSONL persistence — _load_history_from_file
# ---------------------------------------------------------------------------

class TestLoadHistoryFromFile(unittest.TestCase):
    """Alert manager reads JSONL back into the in-memory deque."""

    def _write_jsonl(self, path: Path, rows: list[dict]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def _alert_row(self, **kwargs) -> dict:
        base = {
            "id": "id-1",
            "rule_id": "r1",
            "timestamp": "2026-03-08T12:00:00",
            "trigger": "custom",
            "severity": "low",
            "title": "Test",
            "message": "msg",
            "context": {},
            "channels": ["webhook"],
            "delivered": None,
            "delivery_attempts": 0,
            "delivery_errors": [],
        }
        base.update(kwargs)
        return base

    def test_load_populates_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            self._write_jsonl(path, [
                self._alert_row(id="a1", title="First"),
                self._alert_row(id="a2", title="Second"),
            ])
            manager = AlertManager(history_path=path)
            history = manager.get_history()
            self.assertEqual(len(history), 2)

    def test_load_order_newest_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            self._write_jsonl(path, [
                self._alert_row(id="a1", title="Older"),
                self._alert_row(id="a2", title="Newer"),
            ])
            manager = AlertManager(history_path=path)
            history = manager.get_history()
            self.assertEqual(history[0].title, "Newer")

    def test_load_skips_invalid_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            path.write_text('{"id": "a1", "rule_id": "r1", "timestamp": "2026-03-08T12:00:00", '
                            '"trigger": "custom", "severity": "low", "title": "Good", '
                            '"message": "m", "context": {}, "channels": [], '
                            '"delivered": null, "delivery_attempts": 0, "delivery_errors": []}\n'
                            'NOT_JSON\n')
            manager = AlertManager(history_path=path)
            history = manager.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].title, "Good")

    def test_load_respects_max_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            rows = [self._alert_row(id=f"id-{i}", title=f"Alert{i}") for i in range(20)]
            self._write_jsonl(path, rows)
            manager = AlertManager(max_history=5, history_path=path)
            history = manager.get_history()
            self.assertLessEqual(len(history), 5)

    def test_load_nonexistent_file_is_noop(self):
        manager = AlertManager(history_path=Path("/nonexistent/path/alerts.jsonl"))
        history = manager.get_history()
        self.assertEqual(history, [])

    def test_load_is_lazy_first_call_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            self._write_jsonl(path, [self._alert_row(title="Loaded")])
            manager = AlertManager(history_path=path)
            self.assertFalse(manager._history_loaded)
            manager.get_history()
            self.assertTrue(manager._history_loaded)


# ---------------------------------------------------------------------------
# _row_to_alert
# ---------------------------------------------------------------------------

class TestRowToAlert(unittest.TestCase):
    """AlertManager._row_to_alert reconstructs Alert from a dict."""

    def _valid_row(self, **kwargs) -> dict:
        base = {
            "id": "test-id",
            "rule_id": "r1",
            "timestamp": "2026-03-08T12:00:00",
            "trigger": "custom",
            "severity": "medium",
            "title": "My Alert",
            "message": "Some message",
            "context": {"key": "value"},
            "channels": ["email", "webhook"],
            "delivered": None,
            "delivery_attempts": 2,
            "delivery_errors": ["err1"],
        }
        base.update(kwargs)
        return base

    def test_reconstructs_basic_alert(self):
        row = self._valid_row()
        alert = AlertManager._row_to_alert(row)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.id, "test-id")
        self.assertEqual(alert.title, "My Alert")

    def test_reconstructs_severity_enum(self):
        row = self._valid_row(severity="critical")
        alert = AlertManager._row_to_alert(row)
        self.assertEqual(alert.severity, AlertSeverity.CRITICAL)

    def test_reconstructs_trigger_enum(self):
        row = self._valid_row(trigger="circuit_breaker")
        alert = AlertManager._row_to_alert(row)
        self.assertEqual(alert.trigger, AlertTrigger.CIRCUIT_BREAKER)

    def test_reconstructs_channels(self):
        row = self._valid_row(channels=["email", "webhook"])
        alert = AlertManager._row_to_alert(row)
        self.assertIn(ChannelType.EMAIL, alert.channels)
        self.assertIn(ChannelType.WEBHOOK, alert.channels)

    def test_reconstructs_delivered_timestamp(self):
        row = self._valid_row(delivered="2026-03-08T12:05:00")
        alert = AlertManager._row_to_alert(row)
        self.assertIsNotNone(alert.delivered)
        self.assertEqual(alert.delivered.hour, 12)

    def test_delivered_none_stays_none(self):
        row = self._valid_row(delivered=None)
        alert = AlertManager._row_to_alert(row)
        self.assertIsNone(alert.delivered)

    def test_delivery_attempts_restored(self):
        row = self._valid_row(delivery_attempts=3)
        alert = AlertManager._row_to_alert(row)
        self.assertEqual(alert.delivery_attempts, 3)

    def test_delivery_errors_restored(self):
        row = self._valid_row(delivery_errors=["fail1", "fail2"])
        alert = AlertManager._row_to_alert(row)
        self.assertEqual(alert.delivery_errors, ["fail1", "fail2"])

    def test_invalid_row_returns_none(self):
        result = AlertManager._row_to_alert({"garbage": "data"})
        self.assertIsNone(result)

    def test_invalid_trigger_returns_none(self):
        row = self._valid_row(trigger="not_a_real_trigger")
        result = AlertManager._row_to_alert(row)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# set_history_path
# ---------------------------------------------------------------------------

class TestSetHistoryPath(unittest.TestCase):
    """set_history_path updates path and resets lazy-load flag."""

    def test_set_history_path_updates_path(self):
        manager = AlertManager()
        new_path = Path("/tmp/new_alerts.jsonl")
        manager.set_history_path(new_path)
        self.assertEqual(manager._history_path, new_path)

    def test_set_history_path_resets_loaded_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = AlertManager(history_path=path)
            manager.get_history()  # triggers load, sets _history_loaded = True
            self.assertTrue(manager._history_loaded)
            manager.set_history_path(Path(tmpdir) / "new.jsonl")
            self.assertFalse(manager._history_loaded)

    def test_set_history_path_then_get_history_loads_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = Path(tmpdir) / "file1.jsonl"
            path2 = Path(tmpdir) / "file2.jsonl"

            row = json.dumps({
                "id": "x1", "rule_id": "r", "timestamp": "2026-03-08T10:00:00",
                "trigger": "custom", "severity": "low", "title": "From File2",
                "message": "m", "context": {}, "channels": [],
                "delivered": None, "delivery_attempts": 0, "delivery_errors": [],
            })
            path2.write_text(row + "\n")

            manager = AlertManager(history_path=path1)
            manager.get_history()  # loads empty file1

            manager.set_history_path(path2)
            history = manager.get_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].title, "From File2")


# ---------------------------------------------------------------------------
# End-to-end: trigger_alert persists to JSONL
# ---------------------------------------------------------------------------

class TestTriggerAlertPersistence(unittest.IsolatedAsyncioTestCase):
    """trigger_alert appends alerts to JSONL file."""

    async def test_trigger_alert_writes_to_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = _make_manager_with_rule(history_path=path)

            # Mock the channel so we don't need a real webhook
            mock_channel = AsyncMock()
            mock_channel.send.return_value = True
            manager.register_channel(ChannelType.WEBHOOK, mock_channel)

            await manager.trigger_alert(
                trigger_type=AlertTrigger.CUSTOM,
                severity=AlertSeverity.LOW,
                title="Persisted Alert",
                message="Should be on disk",
            )

            self.assertTrue(path.exists())
            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["title"], "Persisted Alert")

    async def test_trigger_alert_multiple_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "alerts.jsonl"
            manager = _make_manager_with_rule(history_path=path)

            mock_channel = AsyncMock()
            mock_channel.send.return_value = True
            manager.register_channel(ChannelType.WEBHOOK, mock_channel)

            for i in range(3):
                await manager.trigger_alert(
                    trigger_type=AlertTrigger.CUSTOM,
                    severity=AlertSeverity.LOW,
                    title=f"Alert {i}",
                    message="msg",
                )

            lines = path.read_text().strip().splitlines()
            self.assertEqual(len(lines), 3)

    async def test_trigger_alert_no_path_does_not_crash(self):
        manager = _make_manager_with_rule()  # no path

        mock_channel = AsyncMock()
        mock_channel.send.return_value = True
        manager.register_channel(ChannelType.WEBHOOK, mock_channel)

        alerts = await manager.trigger_alert(
            trigger_type=AlertTrigger.CUSTOM,
            severity=AlertSeverity.LOW,
            title="No Persist",
            message="msg",
        )
        self.assertEqual(len(alerts), 1)


# ---------------------------------------------------------------------------
# Telegram warning in runtime._build_webhook_channel
# ---------------------------------------------------------------------------

class TestRuntimeTelegramWarning(unittest.TestCase):
    """configure_alerts warns when Telegram type is set but chat_id is missing."""

    def test_telegram_missing_chat_id_prints_warning(self):
        import config
        from alerts.runtime import _build_webhook_channel

        with patch.object(config, "ALERT_WEBHOOK_URL", "https://api.telegram.org/botTOKEN/sendMessage"), \
             patch.object(config, "ALERT_WEBHOOK_TYPE", "telegram"), \
             patch.object(config, "ALERT_TELEGRAM_CHAT_ID", ""), \
             patch.object(config, "ALERT_WEBHOOK_RETRY_ATTEMPTS", 3), \
             patch.object(config, "ALERT_WEBHOOK_TIMEOUT_SECONDS", 10):
            import io
            import sys
            captured = io.StringIO()
            sys.stdout = captured
            try:
                channel = _build_webhook_channel()
            finally:
                sys.stdout = sys.__stdout__
            output = captured.getvalue()
            self.assertIn("telegram", output.lower())
            self.assertIn("ALERT_TELEGRAM_CHAT_ID", output)

    def test_telegram_with_chat_id_no_warning(self):
        import config
        from alerts.runtime import _build_webhook_channel

        with patch.object(config, "ALERT_WEBHOOK_URL", "https://api.telegram.org/botTOKEN/sendMessage"), \
             patch.object(config, "ALERT_WEBHOOK_TYPE", "telegram"), \
             patch.object(config, "ALERT_TELEGRAM_CHAT_ID", "123456789"), \
             patch.object(config, "ALERT_WEBHOOK_RETRY_ATTEMPTS", 3), \
             patch.object(config, "ALERT_WEBHOOK_TIMEOUT_SECONDS", 10):
            import io
            import sys
            captured = io.StringIO()
            sys.stdout = captured
            try:
                channel = _build_webhook_channel()
            finally:
                sys.stdout = sys.__stdout__
            output = captured.getvalue()
            self.assertNotIn("ALERT_TELEGRAM_CHAT_ID", output)

    def test_telegram_channel_has_correct_chat_id(self):
        import config
        from alerts.runtime import _build_webhook_channel

        with patch.object(config, "ALERT_WEBHOOK_URL", "https://api.telegram.org/botTOKEN/sendMessage"), \
             patch.object(config, "ALERT_WEBHOOK_TYPE", "telegram"), \
             patch.object(config, "ALERT_TELEGRAM_CHAT_ID", "987654321"), \
             patch.object(config, "ALERT_WEBHOOK_RETRY_ATTEMPTS", 3), \
             patch.object(config, "ALERT_WEBHOOK_TIMEOUT_SECONDS", 10):
            channel = _build_webhook_channel()
            self.assertIsNotNone(channel)
            self.assertEqual(channel.telegram_chat_id, "987654321")


if __name__ == "__main__":
    unittest.main()
