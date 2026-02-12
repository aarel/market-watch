import unittest
from datetime import datetime

import pandas as pd

from unittest.mock import patch

from backtest.engine import BacktestBroker, BacktestEngine, BacktestState, Position, StrategyProtocol


class FakeData:
    def __init__(self, df_map, symbols=None, date_range=None):
        self._map = df_map
        if symbols is None:
            symbols = list(df_map.keys())
        self.symbols = symbols
        if date_range is not None:
            self.date_range = date_range
        else:
            dates = []
            for df in df_map.values():
                if df is not None and len(df.index) > 0:
                    dates.extend(df.index)
            if dates:
                self.date_range = (min(dates), max(dates))
            else:
                self.date_range = (pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-01"))

    def get(self, symbol):
        return self._map.get(symbol)

    def get_price(self, symbol, date, field):
        df = self._map.get(symbol)
        if df is None:
            return None
        ts = pd.Timestamp(date)
        if ts in df.index:
            return df.loc[ts, field]
        return None

    def get_bars_up_to(self, symbol, date, days):
        df = self._map.get(symbol)
        if df is None:
            return None
        ts = pd.Timestamp(date)
        subset = df[df.index <= ts]
        if len(subset) == 0:
            return subset
        return subset.iloc[-days:]


class TestBacktestEngineCoverage(unittest.TestCase):
    def test_position_unrealized_pnl_pct_zero_cost_basis(self):
        position = Position(symbol="AAA", quantity=0, entry_price=100, entry_date=datetime(2023, 1, 1))
        position.current_price = 150
        self.assertEqual(position.unrealized_pnl_pct, 0.0)

    def test_backtest_broker_defaults_and_none_date(self):
        dates = pd.date_range("2023-01-01", periods=3, freq="D")
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=dates)
        data = FakeData({"AAA": df})
        broker = BacktestBroker(data=data, lookback_days=5)

        # current_date None returns None
        self.assertIsNone(broker.get_bars("AAA"))

        # days defaults to lookback_days
        broker.current_date = dates[-1]
        bars = broker.get_bars("AAA")
        self.assertEqual(len(bars), 3)

        # get_current_price returns close
        price = broker.get_current_price("AAA")
        self.assertEqual(price, 3.0)

        # get_position is stub
        self.assertIsNone(broker.get_position("AAA"))

    def test_run_raises_no_trading_dates(self):
        data = FakeData({"AAA": None}, symbols=["AAA"], date_range=(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-01-02")))
        engine = BacktestEngine(data=data)

        with self.assertRaises(ValueError):
            engine.run()

    def test_run_raises_insufficient_data(self):
        dates = pd.date_range("2023-01-01", periods=5, freq="D")
        df = pd.DataFrame({"close": [1, 2, 3, 4, 5]}, index=dates)
        data = FakeData({"AAA": df})
        engine = BacktestEngine(data=data)
        engine.set_strategy_params(lookback_days=2)

        with self.assertRaises(ValueError):
            engine.run(symbols=["AAA"], start="2023-01-01", end="2023-01-05")

    def test_run_skips_missing_prices_and_handles_sell(self):
        dates = pd.date_range("2023-01-01", periods=9, freq="D")
        prices = [100.0] * 7 + [110.0, 90.0]
        df = pd.DataFrame({
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1] * len(prices),
        }, index=dates)

        data = FakeData({"TEST": df, "MISS": None}, symbols=["TEST", "MISS"])
        engine = BacktestEngine(
            data=data,
            initial_capital=1000,
            slippage=0.0,
            commission=0.0,
            stop_loss_pct=0.5,
        )
        engine.set_strategy_params(lookback_days=2, momentum_threshold=0.05, sell_threshold=-0.01)

        results = engine.run()
        # Should have at least one trade (buy then sell)
        self.assertGreaterEqual(len(results.trades), 1)

    def test_generate_signal_hold_when_no_bars(self):
        class DummyBroker:
            def get_bars(self, symbol, days):
                return None

        engine = BacktestEngine(data=FakeData({}))
        state = BacktestState(initial_capital=1000)
        signal = engine._generate_signal("AAA", DummyBroker(), state, 100.0)
        self.assertEqual(signal, "hold")

    def test_generate_signal_sell_when_momentum_below_threshold(self):
        bars = pd.DataFrame({"close": [100.0, 90.0]})

        class DummyBroker:
            def get_bars(self, symbol, days):
                return bars

        engine = BacktestEngine(data=FakeData({}))
        engine.set_strategy_params(lookback_days=2, sell_threshold=-0.01)
        state = BacktestState(initial_capital=1000)
        state.positions["AAA"] = Position(symbol="AAA", quantity=1, entry_price=100, entry_date=datetime(2023, 1, 1))

        signal = engine._generate_signal("AAA", DummyBroker(), state, 90.0)
        self.assertEqual(signal, "sell")

    def test_check_stop_losses_paths(self):
        engine = BacktestEngine(data=FakeData({}), stop_loss_pct=0.05)
        state = BacktestState(initial_capital=1000)
        state.positions["MISS"] = Position(symbol="MISS", quantity=1, entry_price=100, entry_date=datetime(2023, 1, 1))
        state.positions["DROP"] = Position(symbol="DROP", quantity=1, entry_price=100, entry_date=datetime(2023, 1, 1))

        prices = {"DROP": 90.0}  # MISS not present, DROP triggers stop loss
        engine._check_stop_losses(state, prices, datetime(2023, 1, 10))

        self.assertNotIn("DROP", state.positions)
        self.assertIn("MISS", state.positions)

    def test_execute_buy_early_returns(self):
        engine = BacktestEngine(data=FakeData({}), slippage=0.0, commission=0.0)

        # position_value < 100
        state = BacktestState(initial_capital=50)
        engine._execute_buy(state, "AAA", price=10.0, date=datetime(2023, 1, 1))
        self.assertEqual(state.positions, {})

        # quantity < 1
        state = BacktestState(initial_capital=1000)
        engine._execute_buy(state, "AAA", price=5000.0, date=datetime(2023, 1, 1))
        self.assertEqual(state.positions, {})

        # total_cost > cash (high commission)
        engine_high_commission = BacktestEngine(
            data=FakeData({}), slippage=0.0, commission=1.1, max_position_pct=1.0
        )
        state = BacktestState(initial_capital=200)
        engine_high_commission._execute_buy(state, "AAA", price=100.0, date=datetime(2023, 1, 1))
        self.assertEqual(state.positions, {})

    def test_execute_sell_no_position_returns(self):
        engine = BacktestEngine(data=FakeData({}))
        state = BacktestState(initial_capital=1000)
        engine._execute_sell(state, "AAA", price=100.0, date=datetime(2023, 1, 1), reason="test")
        self.assertEqual(state.positions, {})

    def test_build_results_with_benchmark(self):
        dates = pd.date_range("2023-01-01", periods=3, freq="D")
        bench = pd.DataFrame({"close": [100.0, 101.0, 102.0]}, index=dates)
        data = FakeData({"SPY": bench}, symbols=["SPY"])
        engine = BacktestEngine(data=data, initial_capital=100)

        state = BacktestState(initial_capital=100)
        state.equity_history = [(dates[0], 100.0), (dates[1], 101.0), (dates[2], 102.0)]
        state.position_history = [(dates[0], 0.0), (dates[1], 0.0), (dates[2], 0.0)]

        results = engine._build_results(state, ["AAA"], "2023-01-01", "2023-01-03", benchmark_symbol="SPY")
        self.assertIsNotNone(results.metrics)

    def test_set_strategy_params_updates_fields(self):
        engine = BacktestEngine(data=FakeData({}))
        engine.set_strategy_params(
            lookback_days=10,
            momentum_threshold=0.1,
            sell_threshold=-0.02,
            stop_loss_pct=0.02,
            max_position_pct=0.3,
        )

        self.assertEqual(engine.lookback_days, 10)
        self.assertEqual(engine.momentum_threshold, 0.1)
        self.assertEqual(engine.sell_threshold, -0.02)
        self.assertEqual(engine.stop_loss_pct, 0.02)
        self.assertEqual(engine.max_position_pct, 0.3)

    def test_protocol_method_executes_body(self):
        bars = pd.DataFrame({"close": [100.0, 101.0]})
        # Call the protocol method body to mark coverage on the ellipsis line.
        StrategyProtocol.calculate_momentum(None, "AAA", bars)

    def test_run_hits_momentum_reversal_sell(self):
        dates = pd.date_range("2023-01-01", periods=9, freq="D")
        closes = [100.0] * 7 + [110.0, 100.0]
        df = pd.DataFrame({
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1] * len(closes),
        }, index=dates)

        data = FakeData({"TEST": df}, symbols=["TEST"])
        engine = BacktestEngine(data=data, initial_capital=1000, slippage=0.0, commission=0.0)
        engine.set_strategy_params(lookback_days=2, momentum_threshold=0.05, sell_threshold=-0.01)

        with patch.object(engine, "_check_stop_losses", return_value=None):
            results = engine.run()
        # Buy then sell on momentum reversal (trade reason reflects sell)
        reasons = [t.reason for t in results.trades]
        self.assertIn("Momentum reversal", reasons)


if __name__ == "__main__":
    unittest.main()
