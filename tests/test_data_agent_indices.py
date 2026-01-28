import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from agents.data_agent import DataAgent
from agents.event_bus import EventBus
from universe import Universe, UniverseContext
import config


class DummySnapshot:
    def __init__(self, price: float, prev_close: float):
        self.latest_trade = SimpleNamespace(price=price)
        self.prev_daily_bar = SimpleNamespace(c=prev_close)


class DummyBroker:
    def __init__(self):
        self.snapshots_requested = []

    def is_market_open(self):
        return True

    def get_account(self):
        return SimpleNamespace(
            portfolio_value=100000,
            buying_power=100000,
            cash=50000,
            equity=100000,
        )

    def get_positions(self):
        return []

    def get_snapshots(self, symbols):
        self.snapshots_requested.append(list(symbols))
        return {symbol: DummySnapshot(price=110.0, prev_close=100.0) for symbol in symbols}

    def get_current_price(self, symbol):
        return 10.0

    def get_bars(self, symbol, days=20):
        return pd.DataFrame(
            {
                "open": [10, 11],
                "high": [11, 12],
                "low": [9, 10],
                "close": [10, 11],
                "volume": [1000, 1200],
            }
        )


class TestDataAgentMarketIndices(unittest.IsolatedAsyncioTestCase):
    async def test_market_indices_included(self):
        broker = DummyBroker()
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = DataAgent(bus, broker, interval_minutes=1)

        with patch.object(config, "WATCHLIST_MODE", "static"), \
            patch.object(config, "WATCHLIST", ["AAA"]), \
            patch.object(config, "LOOKBACK_DAYS", 2), \
            patch.object(config, "MARKET_INDEX_SYMBOLS", ["SPY", "QQQ"]):
            event = await agent.fetch_data(symbols=["AAA"])

        indices = {entry["symbol"]: entry for entry in event.market_indices}
        self.assertIn("SPY", indices)
        self.assertIn("QQQ", indices)
        self.assertAlmostEqual(indices["SPY"]["change_pct"], 0.1)
        self.assertAlmostEqual(indices["QQQ"]["change_pct"], 0.1)


if __name__ == "__main__":
    unittest.main()
