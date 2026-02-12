import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

import server.dependencies as deps


class TestServerDependenciesCoverage(unittest.TestCase):
    def test_get_state_uses_app_state_instance(self):
        sentinel = SimpleNamespace(name="state")
        with patch("server.dependencies.AppState.instance", return_value=sentinel):
            result = deps.get_state()
        self.assertIs(result, sentinel)

    def test_get_config_manager_returns_state_config(self):
        cfg = SimpleNamespace(name="cfg")
        state = SimpleNamespace(config_manager=cfg)
        self.assertIs(deps.get_config_manager(state), cfg)

    def test_get_broker_raises_when_missing(self):
        state = SimpleNamespace(broker=None)
        with self.assertRaises(HTTPException) as ctx:
            deps.get_broker(state)
        self.assertEqual(ctx.exception.status_code, 503)

    def test_get_broker_returns_broker(self):
        broker = SimpleNamespace(name="broker")
        state = SimpleNamespace(broker=broker)
        self.assertIs(deps.get_broker(state), broker)

    def test_get_analytics_store_disabled_or_missing(self):
        state = SimpleNamespace(analytics_store=None)
        with patch("server.dependencies.config.ANALYTICS_ENABLED", False):
            with self.assertRaises(HTTPException) as ctx:
                deps.get_analytics_store(state)
            self.assertEqual(ctx.exception.status_code, 503)

        with patch("server.dependencies.config.ANALYTICS_ENABLED", True):
            with self.assertRaises(HTTPException) as ctx:
                deps.get_analytics_store(state)
            self.assertEqual(ctx.exception.status_code, 503)

    def test_get_analytics_store_returns_store(self):
        store = SimpleNamespace(name="store")
        state = SimpleNamespace(analytics_store=store)
        with patch("server.dependencies.config.ANALYTICS_ENABLED", True):
            self.assertIs(deps.get_analytics_store(state), store)


if __name__ == "__main__":
    unittest.main()
