import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from server.routers.alerts import TestAlertRequest, get_alert_history, test_alert


class DummyAlert:
    def __init__(self, delivered=None, errors=None):
        self.delivered = delivered
        self.delivery_errors = errors or []

    def to_dict(self):
        return {"id": "alert-1"}


class TestAlertsRouterCoverage(unittest.IsolatedAsyncioTestCase):
    async def test_get_alert_history_returns_dicts(self):
        alert = DummyAlert()
        manager = SimpleNamespace(get_history=Mock(return_value=[alert]))
        with patch("server.routers.alerts.get_manager", return_value=manager):
            result = await get_alert_history(limit=1, state=None)

        self.assertEqual(result["alerts"], [{"id": "alert-1"}])

    async def test_test_alert_success_delivered(self):
        delivered_at = datetime.utcnow()
        alert = DummyAlert(delivered=delivered_at)
        manager = SimpleNamespace(trigger_alert=AsyncMock(return_value=[alert]))
        with patch("server.routers.alerts.get_manager", return_value=manager):
            result = await test_alert(TestAlertRequest(channel="email"), state=None)

        self.assertTrue(result["success"])
        self.assertIn("successfully", result["message"])
        self.assertEqual(result["errors"], [])

    async def test_test_alert_created_but_not_delivered(self):
        alert = DummyAlert(delivered=None, errors=["delivery failed"])
        manager = SimpleNamespace(trigger_alert=AsyncMock(return_value=[alert]))
        with patch("server.routers.alerts.get_manager", return_value=manager):
            result = await test_alert(TestAlertRequest(channel="email"), state=None)

        self.assertFalse(result["success"])
        self.assertIn("delivery failed", result["message"].lower())
        self.assertEqual(result["errors"], ["delivery failed"])

    async def test_test_alert_no_rules_configured(self):
        manager = SimpleNamespace(trigger_alert=AsyncMock(return_value=[]))
        with patch("server.routers.alerts.get_manager", return_value=manager):
            result = await test_alert(TestAlertRequest(channel="webhook"), state=None)

        self.assertFalse(result["success"])
        self.assertIn("No alert rules", result["message"])
        self.assertEqual(result["errors"], [])

    async def test_test_alert_exception(self):
        manager = SimpleNamespace(trigger_alert=AsyncMock(side_effect=Exception("boom")))
        with patch("server.routers.alerts.get_manager", return_value=manager):
            result = await test_alert(TestAlertRequest(channel="email"), state=None)

        self.assertFalse(result["success"])
        self.assertIn("Failed to send test alert", result["message"])
        self.assertEqual(result["errors"], ["boom"])


if __name__ == "__main__":
    unittest.main()
