"""Tests for the broker abstraction layer (Phase 6).

Covers:
  - BaseBroker is a proper ABC (cannot be instantiated directly)
  - FakeBroker satisfies BaseBroker (isinstance, all abstract methods present)
  - IBKRBroker satisfies BaseBroker (isinstance, all abstract methods present)
  - IBKRBroker is constructable without a network connection
  - IBKRBroker trading methods raise NotImplementedError
  - IBKRBroker.capabilities() returns structured data
  - IBKRBroker rejects SIMULATION universe
  - BROKER_TYPE config routing (alpaca vs ibkr)
  - config.BROKER_TYPE defaults to "alpaca"
"""
import os
import unittest
from unittest.mock import patch

from brokers.base import BaseBroker
from brokers.ibkr import IBKRBroker
from fake_broker import FakeBroker
from universe import Universe


# ---------------------------------------------------------------------------
# BaseBroker is abstract
# ---------------------------------------------------------------------------

class TestBaseBrokerIsAbstract(unittest.TestCase):

    def test_cannot_instantiate_directly(self):
        """BaseBroker is abstract — direct instantiation must raise TypeError."""
        with self.assertRaises(TypeError):
            BaseBroker()

    def test_is_abc(self):
        """BaseBroker uses ABC machinery."""
        from abc import ABCMeta
        self.assertIsInstance(BaseBroker, ABCMeta)

    def test_has_required_abstract_methods(self):
        """All 14 core methods are declared as abstract on BaseBroker."""
        required = {
            "get_account", "get_buying_power", "get_portfolio_value",
            "get_positions", "get_position",
            "get_bars", "get_snapshots", "get_current_price",
            "submit_order", "list_orders", "list_all_orders",
            "is_market_open", "get_next_market_open", "get_next_market_close",
            "get_asset_names",
        }
        abstract = getattr(BaseBroker, "__abstractmethods__", set())
        for method in required:
            self.assertIn(method, abstract, f"Expected {method} to be abstract")


# ---------------------------------------------------------------------------
# FakeBroker satisfies BaseBroker
# ---------------------------------------------------------------------------

class TestFakeBrokerInterface(unittest.TestCase):

    def setUp(self):
        self.broker = FakeBroker(universe=Universe.SIMULATION)

    def test_isinstance_of_base_broker(self):
        self.assertIsInstance(self.broker, BaseBroker)

    def test_all_abstract_methods_implemented(self):
        """FakeBroker has no unimplemented abstract methods."""
        remaining = getattr(self.broker.__class__, "__abstractmethods__", set())
        self.assertEqual(remaining, set(),
                         f"FakeBroker still has unimplemented abstract methods: {remaining}")

    def test_get_account_returns_object(self):
        acct = self.broker.get_account()
        self.assertIsNotNone(acct)

    def test_get_buying_power_returns_float(self):
        bp = self.broker.get_buying_power()
        self.assertIsInstance(bp, float)

    def test_get_portfolio_value_returns_float(self):
        pv = self.broker.get_portfolio_value()
        self.assertIsInstance(pv, float)

    def test_get_positions_returns_list(self):
        positions = self.broker.get_positions()
        self.assertIsInstance(positions, list)

    def test_get_position_unknown_symbol_returns_none(self):
        result = self.broker.get_position("ZZZZZZ")
        self.assertIsNone(result)

    def test_get_bars_returns_dataframe(self):
        import pandas as pd
        df = self.broker.get_bars("AAPL", days=5)
        self.assertIsInstance(df, pd.DataFrame)

    def test_get_snapshots_returns_dict(self):
        snaps = self.broker.get_snapshots(["AAPL"])
        self.assertIsInstance(snaps, dict)

    def test_get_current_price_returns_numeric(self):
        price = self.broker.get_current_price("AAPL")
        self.assertIsNotNone(price)
        self.assertIsInstance(price, (int, float))

    def test_is_market_open_returns_bool(self):
        result = self.broker.is_market_open()
        self.assertIsInstance(result, bool)

    def test_get_next_market_open_returns_value(self):
        result = self.broker.get_next_market_open()
        self.assertIsNotNone(result)

    def test_get_next_market_close_returns_value(self):
        result = self.broker.get_next_market_close()
        self.assertIsNotNone(result)

    def test_get_asset_names_returns_dict(self):
        names = self.broker.get_asset_names(["AAPL", "MSFT"])
        self.assertIsInstance(names, dict)

    def test_list_orders_returns_list(self):
        orders = self.broker.list_orders()
        self.assertIsInstance(orders, list)

    def test_list_all_orders_returns_list(self):
        orders = self.broker.list_all_orders()
        self.assertIsInstance(orders, list)


# ---------------------------------------------------------------------------
# IBKRBroker satisfies BaseBroker
# ---------------------------------------------------------------------------

class TestIBKRBrokerInterface(unittest.TestCase):

    def setUp(self):
        self.broker = IBKRBroker(universe=Universe.PAPER)

    def test_isinstance_of_base_broker(self):
        self.assertIsInstance(self.broker, BaseBroker)

    def test_all_abstract_methods_implemented(self):
        remaining = getattr(self.broker.__class__, "__abstractmethods__", set())
        self.assertEqual(remaining, set(),
                         f"IBKRBroker still has unimplemented abstract methods: {remaining}")

    def test_constructable_without_network(self):
        """Constructor must not open a network connection."""
        # If constructor attempted a network call to 127.0.0.1:7497 and failed,
        # it would raise ConnectionRefusedError — must not happen.
        broker = IBKRBroker(universe=Universe.LIVE)
        self.assertIsNotNone(broker)

    def test_constructor_stores_config(self):
        broker = IBKRBroker(
            universe=Universe.PAPER,
            host="192.168.1.100",
            port=4002,
            client_id=5,
            account="DU123456",
        )
        self.assertEqual(broker.host, "192.168.1.100")
        self.assertEqual(broker.port, 4002)
        self.assertEqual(broker.client_id, 5)
        self.assertEqual(broker.account, "DU123456")

    def test_constructor_defaults_from_env(self):
        """Constructor uses environment variables for defaults."""
        with patch.dict(os.environ, {"IBKR_HOST": "10.0.0.1", "IBKR_PORT": "4002", "IBKR_CLIENT_ID": "3"}):
            broker = IBKRBroker(universe=Universe.PAPER)
        self.assertEqual(broker.host, "10.0.0.1")
        self.assertEqual(broker.port, 4002)
        self.assertEqual(broker.client_id, 3)

    def test_rejects_simulation_universe(self):
        with self.assertRaises(ValueError):
            IBKRBroker(universe=Universe.SIMULATION)

    def test_rejects_non_universe_type(self):
        with self.assertRaises(TypeError):
            IBKRBroker(universe="paper")


class TestIBKRBrokerTradingMethodsRaiseNotImplemented(unittest.TestCase):
    """All trading/data methods must raise NotImplementedError."""

    def setUp(self):
        self.broker = IBKRBroker(universe=Universe.PAPER)

    def _assert_not_implemented(self, method_name, *args, **kwargs):
        with self.assertRaises(NotImplementedError, msg=f"{method_name} should raise NotImplementedError"):
            getattr(self.broker, method_name)(*args, **kwargs)

    def test_connect(self):               self._assert_not_implemented("connect")
    def test_get_account(self):           self._assert_not_implemented("get_account")
    def test_get_buying_power(self):      self._assert_not_implemented("get_buying_power")
    def test_get_portfolio_value(self):   self._assert_not_implemented("get_portfolio_value")
    def test_get_positions(self):         self._assert_not_implemented("get_positions")
    def test_get_position(self):          self._assert_not_implemented("get_position", "AAPL")
    def test_get_bars(self):              self._assert_not_implemented("get_bars", "AAPL")
    def test_get_snapshots(self):         self._assert_not_implemented("get_snapshots", ["AAPL"])
    def test_get_current_price(self):     self._assert_not_implemented("get_current_price", "AAPL")
    def test_submit_order(self):          self._assert_not_implemented("submit_order", "AAPL", qty=1)
    def test_list_orders(self):           self._assert_not_implemented("list_orders")
    def test_list_all_orders(self):       self._assert_not_implemented("list_all_orders")
    def test_is_market_open(self):        self._assert_not_implemented("is_market_open")
    def test_get_next_market_open(self):  self._assert_not_implemented("get_next_market_open")
    def test_get_next_market_close(self): self._assert_not_implemented("get_next_market_close")
    def test_get_asset_names(self):       self._assert_not_implemented("get_asset_names", ["AAPL"])


class TestIBKRBrokerCapabilities(unittest.TestCase):

    def test_capabilities_always_available(self):
        """capabilities() is a static method — no network or universe needed."""
        caps = IBKRBroker.capabilities()
        self.assertIsInstance(caps, dict)

    def test_capabilities_has_required_fields(self):
        caps = IBKRBroker.capabilities()
        for field in ("broker", "status", "supported_universes", "asset_classes",
                      "api_library", "notes"):
            self.assertIn(field, caps, f"Missing capabilities field: {field}")

    def test_capabilities_status_is_stub(self):
        self.assertEqual(IBKRBroker.capabilities()["status"], "stub")

    def test_capabilities_supported_universes(self):
        universes = IBKRBroker.capabilities()["supported_universes"]
        self.assertIn("LIVE", universes)
        self.assertIn("PAPER", universes)


# ---------------------------------------------------------------------------
# BROKER_TYPE config
# ---------------------------------------------------------------------------

class TestBrokerTypeConfig(unittest.TestCase):

    def test_default_broker_type_is_alpaca(self):
        """config.BROKER_TYPE defaults to 'alpaca' if env var not set."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove BROKER_TYPE if set in env to test the default
            env_copy = {k: v for k, v in os.environ.items() if k != "BROKER_TYPE"}
            with patch.dict(os.environ, env_copy, clear=True):
                import importlib
                import config as cfg
                importlib.reload(cfg)
                self.assertEqual(cfg.BROKER_TYPE, "alpaca")

    def test_broker_type_reads_env_var(self):
        """BROKER_TYPE env var is respected."""
        with patch.dict(os.environ, {"BROKER_TYPE": "ibkr"}):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.BROKER_TYPE, "ibkr")

    def test_broker_type_lowercased(self):
        """BROKER_TYPE is normalised to lowercase."""
        with patch.dict(os.environ, {"BROKER_TYPE": "ALPACA"}):
            import importlib
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.BROKER_TYPE, "alpaca")


# ---------------------------------------------------------------------------
# Broker factory routing (lifespan logic, isolated)
# ---------------------------------------------------------------------------

class TestBrokerFactoryRouting(unittest.TestCase):
    """Test the broker selection logic extracted from lifespan.broker_factory."""

    def _broker_factory(self, universe: Universe, broker_type: str):
        """Mirror of the lifespan broker_factory for testing."""
        if universe == Universe.SIMULATION:
            return FakeBroker(universe=universe)
        if broker_type == "ibkr":
            return IBKRBroker(universe=universe)
        if broker_type == "alpaca":
            # Don't instantiate AlpacaBroker in tests (needs real credentials)
            return "AlpacaBroker"  # sentinel
        raise ValueError(f"Unknown BROKER_TYPE: '{broker_type}'")

    def test_simulation_always_fake_broker(self):
        result = self._broker_factory(Universe.SIMULATION, "alpaca")
        self.assertIsInstance(result, FakeBroker)

    def test_simulation_ignores_broker_type(self):
        """Even if BROKER_TYPE=ibkr, SIMULATION must use FakeBroker."""
        result = self._broker_factory(Universe.SIMULATION, "ibkr")
        self.assertIsInstance(result, FakeBroker)

    def test_paper_with_ibkr_type_returns_ibkr_broker(self):
        result = self._broker_factory(Universe.PAPER, "ibkr")
        self.assertIsInstance(result, IBKRBroker)

    def test_live_with_ibkr_type_returns_ibkr_broker(self):
        result = self._broker_factory(Universe.LIVE, "ibkr")
        self.assertIsInstance(result, IBKRBroker)

    def test_paper_with_alpaca_type_returns_alpaca_sentinel(self):
        result = self._broker_factory(Universe.PAPER, "alpaca")
        self.assertEqual(result, "AlpacaBroker")

    def test_unknown_broker_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            self._broker_factory(Universe.PAPER, "td_ameritrade")

    def test_ibkr_broker_from_factory_is_base_broker(self):
        result = self._broker_factory(Universe.PAPER, "ibkr")
        self.assertIsInstance(result, BaseBroker)


if __name__ == "__main__":
    unittest.main()
