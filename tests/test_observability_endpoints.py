import unittest
from unittest.mock import patch
import os

# Disable heavy FastAPI lifespan during unit tests
os.environ.setdefault("FASTAPI_DISABLE_LIFESPAN", "1")

from fastapi import HTTPException

import server


class TestObservabilityEndpoints(unittest.IsolatedAsyncioTestCase):
    async def test_get_observability_expectations(self):
        response = await server.get_observability_expectations()
        self.assertIn("expectations", response)
        expectations = response["expectations"]
        self.assertTrue(expectations)
        self.assertTrue(any(item.get("agent") == "DataAgent" for item in expectations))

    async def test_run_observability_eval_disabled(self):
        with patch.object(server.config, "OBSERVABILITY_ENABLED", False):
            with self.assertRaises(HTTPException) as ctx:
                await server.run_observability_eval()
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_run_observability_eval_eval_disabled(self):
        with patch.object(server.config, "OBSERVABILITY_ENABLED", True), \
            patch.object(server.config, "OBSERVABILITY_EVAL_ENABLED", False):
            with self.assertRaises(HTTPException) as ctx:
                await server.run_observability_eval()
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_run_observability_eval_success(self):
        async def _stub_eval():
            server.state.observability = {"generated_at": "now"}

        with patch.object(server.config, "OBSERVABILITY_ENABLED", True), \
            patch.object(server.config, "OBSERVABILITY_EVAL_ENABLED", True), \
            patch("server._run_observability_eval", new=_stub_eval):
            response = await server.run_observability_eval()

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["latest"], {"generated_at": "now"})


if __name__ == "__main__":
    unittest.main()
