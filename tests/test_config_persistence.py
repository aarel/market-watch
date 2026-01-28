import json
import os
import tempfile
import unittest

import config
import server


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
    "trade_interval": "TRADE_INTERVAL_MINUTES",
    "auto_trade": "AUTO_TRADE",
    "top_gainers_count": "TOP_GAINERS_COUNT",
    "top_gainers_universe": "TOP_GAINERS_UNIVERSE",
    "top_gainers_min_price": "TOP_GAINERS_MIN_PRICE",
    "top_gainers_min_volume": "TOP_GAINERS_MIN_VOLUME",
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
        config.AUTO_TRADE = False
        config.TOP_GAINERS_MIN_PRICE = 12.5
        config.TOP_GAINERS_MIN_VOLUME = 2_000_000

        server.save_config_state()
        # mutate to ensure load repopulates
        config.STRATEGY = "momentum"
        config.WATCHLIST = ["SPY"]
        config.MAX_OPEN_POSITIONS = 10
        config.DAILY_LOSS_LIMIT_PCT = 0.03
        config.MAX_DRAWDOWN_PCT = 0.1
        config.AUTO_TRADE = True
        config.TOP_GAINERS_MIN_PRICE = 5
        config.TOP_GAINERS_MIN_VOLUME = 1_000_000

        server.load_config_state()

        self.assertEqual(config.STRATEGY, "breakout")
        self.assertEqual(config.WATCHLIST, ["AAPL", "MSFT"])
        self.assertEqual(config.MAX_OPEN_POSITIONS, 3)
        self.assertAlmostEqual(config.DAILY_LOSS_LIMIT_PCT, 0.07)
        self.assertAlmostEqual(config.MAX_DRAWDOWN_PCT, 0.2)
        self.assertFalse(config.AUTO_TRADE)
        self.assertEqual(config.TOP_GAINERS_MIN_PRICE, 12.5)
        self.assertEqual(config.TOP_GAINERS_MIN_VOLUME, 2_000_000)

    def test_load_missing_file_no_change(self):
        config.MAX_OPEN_POSITIONS = 11
        # ensure file does not exist
        if os.path.exists(config.CONFIG_STATE_PATH):
            os.remove(config.CONFIG_STATE_PATH)

        server.load_config_state()
        self.assertEqual(config.MAX_OPEN_POSITIONS, 11)

    def test_load_malformed_file_does_not_crash(self):
        # write bad JSON
        with open(config.CONFIG_STATE_PATH, "w", encoding="utf-8") as handle:
            handle.write("{ bad json")
        config.MAX_DAILY_TRADES = 9
        server.load_config_state()
        self.assertEqual(config.MAX_DAILY_TRADES, 9)


if __name__ == "__main__":
    unittest.main()
