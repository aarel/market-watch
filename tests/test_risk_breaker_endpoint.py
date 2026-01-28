import unittest
from unittest.mock import patch
import os

# Disable heavy FastAPI lifespan during unit tests
os.environ.setdefault("FASTAPI_DISABLE_LIFESPAN", "1")

from fastapi import HTTPException

import server


class DummyCoordinator:
    def __init__(self):
        self.reset_called = False

    def reset_circuit_breaker(self):
        self.reset_called = True
        return {"active": False, "reason": None}


class TestRiskBreakerEndpoint(unittest.IsolatedAsyncioTestCase):
    async def test_reset_risk_breaker_requires_coordinator(self):
        original = server.state.coordinator
        server.state.coordinator = None
        try:
            with self.assertRaises(HTTPException) as ctx:
                await server.reset_risk_breaker()
            self.assertEqual(ctx.exception.status_code, 503)
        finally:
            server.state.coordinator = original

    async def test_reset_risk_breaker_calls_coordinator(self):
        coordinator = DummyCoordinator()
        original = server.state.coordinator
        server.state.coordinator = coordinator
        try:
            response = await server.reset_risk_breaker()
        finally:
            server.state.coordinator = original

        self.assertTrue(coordinator.reset_called)
        self.assertEqual(response["status"], "ok")
        self.assertIn("breaker", response)


if __name__ == "__main__":
    unittest.main()
