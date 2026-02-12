import json
import os
import tempfile
import unittest

import config
from server.config_manager import ConfigManager

FIELD_MAP = {
    "strategy": "STRATEGY",
    "watchlist": "WATCHLIST",
    "watchlist_mode": "WATCHLIST_MODE",
    "momentum_threshold": "MOMENTUM_THRESHOLD",
    "sell_threshold": "SELL_THRESHOLD",
    "stop_loss_pct": "STOP_LOSS_PCT",
    "max_position_pct": "MAX_POSITION_PCT",
    "max_daily_trades": "MAX_DAILY_TRADES",
    "max_open_positions": "MAX_OPEN_POSITIONS",
    "daily_loss_limit_pct": "DAILY_LOSS_LIMIT_PCT",
    "max_drawdown_pct": "MAX_DRAWDOWN_PCT",
    "rvol_threshold": "RVOL_THRESHOLD",
    "trade_interval": "TRADE_INTERVAL_MINUTES",
    "auto_trade": "AUTO_TRADE",
    "top_gainers_count": "TOP_GAINERS_COUNT",
    "top_gainers_universe": "TOP_GAINERS_UNIVERSE",
    "top_gainers_min_price": "TOP_GAINERS_MIN_PRICE",
    "top_gainers_min_volume": "TOP_GAINERS_MIN_VOLUME",
    "alerts_enabled": "ALERTS_ENABLED",
    "alert_email_enabled": "ALERT_EMAIL_ENABLED",
    "alert_webhook_enabled": "ALERT_WEBHOOK_ENABLED",
}


def _snapshot():
    return {key: getattr(config, attr) for key, attr in FIELD_MAP.items()}


def _restore(values: dict):
    for key, attr in FIELD_MAP.items():
        if key in values:
            setattr(config, attr, values[key])


class TestConfigPersistence(unittest.TestCase):
    def setUp(self):
        self.original_path = config.CONFIG_STATE_PATH
        self.original_values = _snapshot()
        self.tmpdir = tempfile.TemporaryDirectory()
        config.CONFIG_STATE_PATH = os.path.join(self.tmpdir.name, "config_state.json")
        # Create ConfigManager with explicit path for testing
        self.config_manager = ConfigManager(path=config.CONFIG_STATE_PATH)

    def tearDown(self):
        _restore(self.original_values)
        config.CONFIG_STATE_PATH = self.original_path
        self.tmpdir.cleanup()

    def test_save_and_load_round_trip(self):
        # set distinct values
        config.STRATEGY = "breakout"
        config.WATCHLIST = ["AAPL", "MSFT"]
        config.MAX_OPEN_POSITIONS = 3
        config.DAILY_LOSS_LIMIT_PCT = 0.07
        config.MAX_DRAWDOWN_PCT = 0.2
        config.RVOL_THRESHOLD = 1.3
        config.AUTO_TRADE = False
        config.TOP_GAINERS_MIN_PRICE = 12.5
        config.TOP_GAINERS_MIN_VOLUME = 2_000_000
        config.ALERTS_ENABLED = True
        config.ALERT_EMAIL_ENABLED = True
        config.ALERT_WEBHOOK_ENABLED = False

        self.config_manager.save()
        # mutate to ensure load repopulates
        config.STRATEGY = "momentum"
        config.WATCHLIST = ["SPY"]
        config.MAX_OPEN_POSITIONS = 10
        config.DAILY_LOSS_LIMIT_PCT = 0.03
        config.MAX_DRAWDOWN_PCT = 0.1
        config.RVOL_THRESHOLD = 2.5
        config.AUTO_TRADE = True
        config.TOP_GAINERS_MIN_PRICE = 5
        config.TOP_GAINERS_MIN_VOLUME = 1_000_000
        config.ALERTS_ENABLED = False
        config.ALERT_EMAIL_ENABLED = False
        config.ALERT_WEBHOOK_ENABLED = True

        self.config_manager.load()

        self.assertEqual(config.STRATEGY, "breakout")
        self.assertEqual(config.WATCHLIST, ["AAPL", "MSFT"])
        self.assertEqual(config.MAX_OPEN_POSITIONS, 3)
        self.assertAlmostEqual(config.DAILY_LOSS_LIMIT_PCT, 0.07)
        self.assertAlmostEqual(config.MAX_DRAWDOWN_PCT, 0.2)
        self.assertAlmostEqual(config.RVOL_THRESHOLD, 1.3)
        self.assertFalse(config.AUTO_TRADE)
        self.assertEqual(config.TOP_GAINERS_MIN_PRICE, 12.5)
        self.assertEqual(config.TOP_GAINERS_MIN_VOLUME, 2_000_000)
        self.assertTrue(config.ALERTS_ENABLED)
        self.assertTrue(config.ALERT_EMAIL_ENABLED)
        self.assertFalse(config.ALERT_WEBHOOK_ENABLED)

    def test_load_missing_file_no_change(self):
        config.MAX_OPEN_POSITIONS = 11
        # ensure file does not exist
        if os.path.exists(config.CONFIG_STATE_PATH):
            os.remove(config.CONFIG_STATE_PATH)

        self.config_manager.load()
        self.assertEqual(config.MAX_OPEN_POSITIONS, 11)

    def test_load_malformed_file_does_not_crash(self):
        # write bad JSON
        with open(config.CONFIG_STATE_PATH, "w", encoding="utf-8") as handle:
            handle.write("{ bad json")
        config.MAX_DAILY_TRADES = 9
        self.config_manager.load()
        self.assertEqual(config.MAX_DAILY_TRADES, 9)


class TestBoolCoercionAtBoundary(unittest.TestCase):
    """Test that string booleans arriving via HTTP/JSON are handled correctly.

    This is the exact failure mode the DRA flagged: bool("false") == True.
    Payloads like {"auto_trade": "false"} are common from form submissions
    and some JS clients. The fix lives in RuntimeConfig's field_validator;
    these tests pin that the boundary is safe.
    """

    def setUp(self):
        self.original_values = _snapshot()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_manager = ConfigManager(path=os.path.join(self.tmpdir.name, "config_state.json"))

    def tearDown(self):
        _restore(self.original_values)
        self.tmpdir.cleanup()

    def test_string_false_resolves_to_false(self):
        self.config_manager.apply_updates({"auto_trade": "false"})
        self.assertFalse(self.config_manager.state.auto_trade)
        self.assertFalse(config.AUTO_TRADE)

    def test_string_true_resolves_to_true(self):
        self.config_manager.apply_updates({"auto_trade": "true"})
        self.assertTrue(self.config_manager.state.auto_trade)
        self.assertTrue(config.AUTO_TRADE)

    def test_string_false_case_insensitive(self):
        for variant in ("False", "FALSE", "false", " False "):
            self.config_manager.apply_updates({"auto_trade": variant})
            self.assertFalse(
                self.config_manager.state.auto_trade,
                f"Failed for variant: {variant!r}"
            )

    def test_garbage_string_raises(self):
        with self.assertRaises((ValueError, Exception)):
            self.config_manager.apply_updates({"auto_trade": "nope"})

    def test_native_bool_still_works(self):
        self.config_manager.apply_updates({"auto_trade": False})
        self.assertFalse(self.config_manager.state.auto_trade)
        self.config_manager.apply_updates({"auto_trade": True})
        self.assertTrue(self.config_manager.state.auto_trade)


class TestConfigNamespaceIsolation(unittest.TestCase):
    """Verify that config persistence is universe-scoped, not shared.

    Each universe must write and read its own config_state.json.
    A change in one universe must not appear in another.
    """

    def setUp(self):
        self.original_values = _snapshot()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        # chdir so that get_data_path's relative paths land in tmpdir
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.original_cwd)
        _restore(self.original_values)
        self.tmpdir.cleanup()

    def test_paper_and_simulation_configs_are_isolated(self):
        from universe import Universe

        paper_cm = ConfigManager(universe=Universe.PAPER)
        sim_cm = ConfigManager(universe=Universe.SIMULATION)

        # Write distinct values to each universe
        paper_cm.apply_updates({"max_daily_trades": 42})
        paper_cm.save()

        sim_cm.apply_updates({"max_daily_trades": 7})
        sim_cm.save()

        # Reload from disk — each should see only its own value
        paper_cm2 = ConfigManager(universe=Universe.PAPER)
        sim_cm2 = ConfigManager(universe=Universe.SIMULATION)

        self.assertEqual(paper_cm2.state.max_daily_trades, 42)
        self.assertEqual(sim_cm2.state.max_daily_trades, 7)

    def test_paths_differ_by_universe(self):
        from universe import Universe

        paper_cm = ConfigManager(universe=Universe.PAPER)
        sim_cm = ConfigManager(universe=Universe.SIMULATION)

        self.assertNotEqual(paper_cm.path, sim_cm.path)
        self.assertIn("paper", paper_cm.path)
        self.assertIn("simulation", sim_cm.path)


if __name__ == "__main__":
    unittest.main()
