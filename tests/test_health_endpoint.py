"""
Tests for /health endpoint.
"""
import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

# Disable heavy FastAPI lifespan during unit tests
os.environ.setdefault("FASTAPI_DISABLE_LIFESPAN", "1")

from server.state import AppState
from server.routers import status


class TestHealthEndpoint(unittest.TestCase):
    """Test health check endpoint without spinning up full server."""

    def setUp(self):
        self.state = AppState.instance()
        self.state.start_time = datetime.now()

    def _call(self):
        response = asyncio.run(status.health(state=self.state))
        data = json.loads(response.body.decode())
        return response, data

    def test_health_endpoint_exists(self):
        response, _ = self._call()
        self.assertIn(response.status_code, [200, 503])

    def test_health_response_structure(self):
        _, data = self._call()
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("uptime_seconds", data)
        self.assertIn("checks", data)
        self.assertIn(data["status"], ["healthy", "unhealthy"])
        self.assertIsInstance(data["checks"], dict)

    def test_health_uptime_reasonable(self):
        _, data = self._call()
        uptime = data["uptime_seconds"]
        self.assertGreaterEqual(uptime, 0)
        self.assertLess(uptime, 86400)

    def test_health_timestamp_format(self):
        _, data = self._call()
        parsed = datetime.fromisoformat(data["timestamp"])
        self.assertIsInstance(parsed, datetime)

    def test_health_checks_structure(self):
        _, data = self._call()
        for _, check_data in data["checks"].items():
            self.assertIsInstance(check_data, dict)
            self.assertIn("status", check_data)
            self.assertIn("message", check_data)
            self.assertIn(check_data["status"], ["ok", "degraded", "fail"])

    def test_health_application_check(self):
        _, data = self._call()
        self.assertIn("application", data["checks"])
        self.assertIn(data["checks"]["application"]["status"], ["ok", "degraded", "fail"])

    def test_health_agents_check(self):
        _, data = self._call()
        self.assertIn("agents", data["checks"])
        self.assertIn(data["checks"]["agents"]["status"], ["ok", "degraded", "fail"])

    def test_health_file_system_check(self):
        _, data = self._call()
        self.assertIn("file_system", data["checks"])
        self.assertIn(data["checks"]["file_system"]["status"], ["ok", "degraded", "fail"])

    def test_health_broker_api_check(self):
        _, data = self._call()
        self.assertIn("broker_api", data["checks"])
        self.assertIn(data["checks"]["broker_api"]["status"], ["ok", "degraded", "fail"])

    def test_health_memory_check(self):
        _, data = self._call()
        self.assertIn("memory", data["checks"])
        mem = data["checks"]["memory"]
        self.assertIn(mem["status"], ["ok", "degraded", "fail"])
        if mem["status"] in ["ok", "degraded"]:
            self.assertIn("usage_mb", mem)
            self.assertIn("usage_percent", mem)

    def test_health_no_auth_required(self):
        response, _ = self._call()
        self.assertNotEqual(response.status_code, 401)
        self.assertNotEqual(response.status_code, 403)

    def test_health_returns_503_when_unhealthy(self):
        # Force unhealthy by clearing broker and coordinator
        original = (self.state.broker, self.state.coordinator)
        try:
            self.state.broker = None
            self.state.coordinator = None
            response, data = self._call()
            if data["status"] == "unhealthy":
                self.assertEqual(response.status_code, 503)
            else:
                self.assertEqual(response.status_code, 200)
        finally:
            self.state.broker, self.state.coordinator = original

    def test_health_degraded_when_agents_partial(self):
        mock_coordinator = Mock()
        mock_coordinator.status.return_value = {
            "agents": {
                "data": {"running": True},
                "signal": {"running": False},
                "execution": {"running": True},
            }
        }
        original = (self.state.coordinator, self.state.broker)
        try:
            self.state.coordinator = mock_coordinator
            self.state.broker = Mock()
            self.state.start_time = datetime.now() - timedelta(seconds=100)
            _, data = self._call()
            self.assertNotEqual(data["status"], "healthy")
            self.assertEqual(data["checks"]["agents"]["status"], "degraded")
        finally:
            self.state.coordinator, self.state.broker = original

    def test_health_json_parseable(self):
        response, _ = self._call()
        data = json.loads(response.body.decode())
        self.assertIsInstance(data, dict)


if __name__ == "__main__":
    unittest.main()
