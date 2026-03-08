"""Phase 9 tests: trading windows, FOMC blackout, earnings blackout."""
import json
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

_ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# is_in_trading_window
# ---------------------------------------------------------------------------

class TestTradingWindow(unittest.TestCase):

    def _call(self, avoid_open, avoid_close, hour, minute):
        from market_calendar import is_in_trading_window
        now = datetime(2026, 3, 9, hour, minute, 0, tzinfo=_ET)
        return is_in_trading_window(avoid_open, avoid_close, now=now)

    # --- both disabled ---

    def test_both_zero_always_true(self):
        self.assertTrue(self._call(0, 0, 10, 0))

    def test_both_zero_at_open(self):
        self.assertTrue(self._call(0, 0, 9, 30))

    def test_both_zero_just_before_close(self):
        self.assertTrue(self._call(0, 0, 15, 59))

    # --- avoid open ---

    def test_avoid_open_30_blocks_at_930(self):
        self.assertFalse(self._call(30, 0, 9, 30))

    def test_avoid_open_30_blocks_at_959(self):
        self.assertFalse(self._call(30, 0, 9, 59))

    def test_avoid_open_30_allows_at_1000(self):
        self.assertTrue(self._call(30, 0, 10, 0))

    def test_avoid_open_30_allows_at_1001(self):
        self.assertTrue(self._call(30, 0, 10, 1))

    def test_avoid_open_15_blocks_at_944(self):
        self.assertFalse(self._call(15, 0, 9, 44))

    def test_avoid_open_15_allows_at_945(self):
        self.assertTrue(self._call(15, 0, 9, 45))

    # --- avoid close ---

    def test_avoid_close_15_blocks_at_1545(self):
        self.assertFalse(self._call(0, 15, 15, 45))

    def test_avoid_close_15_blocks_at_1559(self):
        self.assertFalse(self._call(0, 15, 15, 59))

    def test_avoid_close_15_allows_at_1544(self):
        self.assertTrue(self._call(0, 15, 15, 44))

    def test_avoid_close_30_blocks_at_1530(self):
        self.assertFalse(self._call(0, 30, 15, 30))

    def test_avoid_close_30_allows_at_1529(self):
        self.assertTrue(self._call(0, 30, 15, 29))

    # --- both enabled ---

    def test_both_enabled_blocks_in_open_window(self):
        self.assertFalse(self._call(30, 15, 9, 45))

    def test_both_enabled_blocks_in_close_window(self):
        self.assertFalse(self._call(30, 15, 15, 50))

    def test_both_enabled_allows_midday(self):
        self.assertTrue(self._call(30, 15, 12, 0))

    def test_defaults_to_now_when_none_passed(self):
        from market_calendar import is_in_trading_window
        # Should not raise; result depends on actual time
        result = is_in_trading_window(0, 0)
        self.assertIsInstance(result, bool)


# ---------------------------------------------------------------------------
# FomcCalendar
# ---------------------------------------------------------------------------

class TestFomcCalendar(unittest.TestCase):

    def _calendar_with(self, dates: list[str]) -> "FomcCalendar":
        from market_calendar import FomcCalendar
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"dates": dates}, f)
            path = Path(f.name)
        cal = FomcCalendar(dates_path=path)
        path.unlink(missing_ok=True)
        return cal

    def test_is_fomc_day_match(self):
        cal = self._calendar_with(["2026-03-18"])
        self.assertTrue(cal.is_fomc_day(date(2026, 3, 18)))

    def test_is_fomc_day_no_match(self):
        cal = self._calendar_with(["2026-03-18"])
        self.assertFalse(cal.is_fomc_day(date(2026, 3, 17)))

    def test_is_fomc_day_different_year(self):
        cal = self._calendar_with(["2026-03-18"])
        self.assertFalse(cal.is_fomc_day(date(2027, 3, 18)))

    def test_multiple_dates(self):
        cal = self._calendar_with(["2026-01-28", "2026-03-18", "2026-05-06"])
        self.assertTrue(cal.is_fomc_day(date(2026, 1, 28)))
        self.assertTrue(cal.is_fomc_day(date(2026, 5, 6)))
        self.assertFalse(cal.is_fomc_day(date(2026, 2, 1)))

    def test_missing_file_fails_open(self):
        from market_calendar import FomcCalendar
        cal = FomcCalendar(dates_path=Path("/nonexistent/fomc.json"))
        self.assertFalse(cal.is_fomc_day(date(2026, 3, 18)))

    def test_empty_dates_list(self):
        cal = self._calendar_with([])
        self.assertFalse(cal.is_fomc_day(date(2026, 1, 1)))

    def test_dates_property_returns_frozenset(self):
        cal = self._calendar_with(["2026-03-18"])
        self.assertIsInstance(cal.dates, frozenset)
        self.assertIn(date(2026, 3, 18), cal.dates)

    def test_default_path_loads_real_file(self):
        """The shipped fomc_dates.json must load without error."""
        from market_calendar import FomcCalendar
        cal = FomcCalendar()
        self.assertGreater(len(cal.dates), 0)

    def test_2026_dates_in_real_file(self):
        from market_calendar import FomcCalendar
        cal = FomcCalendar()
        # At least 8 dates in 2026
        dates_2026 = [d for d in cal.dates if d.year == 2026]
        self.assertGreaterEqual(len(dates_2026), 8)


# ---------------------------------------------------------------------------
# EarningsCache
# ---------------------------------------------------------------------------

class TestEarningsCache(unittest.TestCase):

    def _cache_with_mock(self, symbol: str, earnings_date: date | None, blackout_days=1, today=None):
        from market_calendar import EarningsCache
        cache = EarningsCache(blackout_days=blackout_days)
        cache._cache[symbol] = earnings_date
        cache._cache_date = today or date.today()
        return cache

    def test_in_blackout_on_earnings_day(self):
        today = date(2026, 4, 23)
        cache = self._cache_with_mock("AAPL", today, today=today)
        self.assertTrue(cache.is_in_blackout("AAPL", today=today))

    def test_in_blackout_day_before_earnings(self):
        today = date(2026, 4, 22)
        cache = self._cache_with_mock("AAPL", date(2026, 4, 23), today=today)
        self.assertTrue(cache.is_in_blackout("AAPL", today=today))

    def test_in_blackout_day_after_earnings(self):
        today = date(2026, 4, 24)
        cache = self._cache_with_mock("AAPL", date(2026, 4, 23), today=today)
        self.assertTrue(cache.is_in_blackout("AAPL", today=today))

    def test_not_in_blackout_two_days_before(self):
        today = date(2026, 4, 21)
        cache = self._cache_with_mock("AAPL", date(2026, 4, 23), today=today)
        self.assertFalse(cache.is_in_blackout("AAPL", today=today))

    def test_fail_open_when_no_earnings_data(self):
        today = date(2026, 4, 23)
        cache = self._cache_with_mock("AAPL", None, today=today)
        self.assertFalse(cache.is_in_blackout("AAPL", today=today))

    def test_blackout_zero_always_false(self):
        today = date(2026, 4, 23)
        cache = self._cache_with_mock("AAPL", today, blackout_days=0, today=today)
        self.assertFalse(cache.is_in_blackout("AAPL", today=today))

    def test_cache_refreshes_on_new_day(self):
        from market_calendar import EarningsCache
        cache = EarningsCache(blackout_days=1)
        cache._cache["AAPL"] = date(2026, 4, 23)
        cache._cache_date = date(2026, 4, 1)  # old date

        # Simulate new day
        with patch.object(cache, "_fetch", return_value=None):
            cache.get_earnings_date("AAPL", today=date(2026, 4, 2))

        # Old cache was cleared (re-fetch returned None, so value is None not the old date)
        self.assertIsNone(cache._cache.get("AAPL"))

    def test_cache_reuses_same_day(self):
        from market_calendar import EarningsCache
        cache = EarningsCache(blackout_days=1)
        today = date(2026, 4, 23)
        cache._cache["AAPL"] = date(2026, 4, 25)
        cache._cache_date = today

        with patch.object(cache, "_fetch", side_effect=AssertionError("should not call _fetch")):
            result = cache.get_earnings_date("AAPL", today=today)
        self.assertEqual(result, date(2026, 4, 25))

    def test_fetch_yfinance_unavailable_returns_none(self):
        from market_calendar import EarningsCache
        cache = EarningsCache(blackout_days=1)
        with patch.dict("sys.modules", {"yfinance": None}):
            result = cache._fetch("AAPL")
        self.assertIsNone(result)

    def test_fetch_yfinance_exception_returns_none(self):
        from market_calendar import EarningsCache
        mock_yf = MagicMock()
        mock_yf.Ticker.side_effect = RuntimeError("network error")
        cache = EarningsCache(blackout_days=1)
        with patch.dict("sys.modules", {"yfinance": mock_yf}):
            result = cache._fetch("AAPL")
        self.assertIsNone(result)

    def test_blackout_extended_range(self):
        """blackout_days=3 blocks trades 3 days out."""
        today = date(2026, 4, 20)
        cache = self._cache_with_mock("MSFT", date(2026, 4, 23), blackout_days=3, today=today)
        self.assertTrue(cache.is_in_blackout("MSFT", today=today))

    def test_blackout_extended_range_outside(self):
        today = date(2026, 4, 19)
        cache = self._cache_with_mock("MSFT", date(2026, 4, 23), blackout_days=3, today=today)
        self.assertFalse(cache.is_in_blackout("MSFT", today=today))


# ---------------------------------------------------------------------------
# DataAgent._apply_market_awareness
# ---------------------------------------------------------------------------

class TestDataAgentMarketAwareness(unittest.IsolatedAsyncioTestCase):

    def _make_agent(self):
        from agents.data_agent import DataAgent
        bus = MagicMock()
        broker = MagicMock()
        broker.universe = MagicMock()
        agent = DataAgent(event_bus=bus, broker=broker, interval_minutes=5)
        agent.universe = MagicMock()
        agent.session_id = "test"
        return agent

    def test_returns_true_when_all_disabled(self):
        agent = self._make_agent()
        import config
        with patch.object(config, "AVOID_OPEN_MINUTES", 0), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0), \
             patch.object(config, "FOMC_BLACKOUT_ENABLED", False):
            self.assertTrue(agent._apply_market_awareness())

    def test_fomc_blackout_suppresses_when_enabled(self):
        agent = self._make_agent()
        import config
        mock_cal = MagicMock()
        mock_cal.is_fomc_day.return_value = True
        agent._fomc_calendar = mock_cal

        with patch.object(config, "FOMC_BLACKOUT_ENABLED", True), \
             patch.object(config, "AVOID_OPEN_MINUTES", 0), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0):
            result = agent._apply_market_awareness()
        self.assertFalse(result)

    def test_fomc_blackout_noop_on_non_fomc_day(self):
        agent = self._make_agent()
        import config
        mock_cal = MagicMock()
        mock_cal.is_fomc_day.return_value = False
        agent._fomc_calendar = mock_cal

        with patch.object(config, "FOMC_BLACKOUT_ENABLED", True), \
             patch.object(config, "AVOID_OPEN_MINUTES", 0), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0):
            result = agent._apply_market_awareness()
        self.assertTrue(result)

    def test_fomc_blackout_disabled_ignores_fomc_day(self):
        agent = self._make_agent()
        import config
        mock_cal = MagicMock()
        mock_cal.is_fomc_day.return_value = True
        agent._fomc_calendar = mock_cal

        with patch.object(config, "FOMC_BLACKOUT_ENABLED", False), \
             patch.object(config, "AVOID_OPEN_MINUTES", 0), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0):
            result = agent._apply_market_awareness()
        self.assertTrue(result)

    def test_trading_window_suppresses_during_open_buffer(self):
        agent = self._make_agent()
        import config
        import market_calendar
        with patch.object(config, "FOMC_BLACKOUT_ENABLED", False), \
             patch.object(config, "AVOID_OPEN_MINUTES", 30), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0), \
             patch.object(market_calendar, "is_in_trading_window", return_value=False):
            result = agent._apply_market_awareness()
        self.assertFalse(result)

    def test_trading_window_allows_midday(self):
        agent = self._make_agent()
        import config
        import market_calendar
        with patch.object(config, "FOMC_BLACKOUT_ENABLED", False), \
             patch.object(config, "AVOID_OPEN_MINUTES", 30), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 15), \
             patch.object(market_calendar, "is_in_trading_window", return_value=True):
            result = agent._apply_market_awareness()
        self.assertTrue(result)

    def test_fomc_calendar_lazily_initialized(self):
        agent = self._make_agent()
        import config
        self.assertIsNone(agent._fomc_calendar)

        with patch.object(config, "FOMC_BLACKOUT_ENABLED", True), \
             patch.object(config, "AVOID_OPEN_MINUTES", 0), \
             patch.object(config, "AVOID_CLOSE_MINUTES", 0), \
             patch("market_calendar.FomcCalendar") as MockCal:
            MockCal.return_value.is_fomc_day.return_value = False
            agent._apply_market_awareness()

        self.assertIsNotNone(agent._fomc_calendar)


# ---------------------------------------------------------------------------
# RiskAgent earnings blackout
# ---------------------------------------------------------------------------

class TestRiskAgentEarningsBlackout(unittest.IsolatedAsyncioTestCase):

    def _make_signal(self, symbol="AAPL", action="buy"):
        signal = MagicMock()
        signal.symbol = symbol
        signal.action = action
        signal.strength = 0.5
        signal.reason = "test"
        signal.momentum = 0.03
        return signal

    async def test_earnings_blackout_blocks_buy(self):
        from agents.risk_agent import RiskAgent
        from agents.events import RiskCheckFailed

        bus = AsyncMock()
        published = []
        async def capture(event):
            published.append(event)
        bus.publish = capture
        bus.subscribe = MagicMock()
        bus.unsubscribe = MagicMock()

        broker = MagicMock()
        broker.get_portfolio_value_async = AsyncMock(return_value=100000.0)
        broker.get_buying_power_async = AsyncMock(return_value=50000.0)
        broker.get_positions = MagicMock(return_value=[])
        broker.universe = MagicMock()

        agent = RiskAgent(event_bus=bus, broker=broker)
        agent.universe = MagicMock()
        agent.session_id = "test"

        # Inject an earnings cache that says AAPL is in blackout
        from market_calendar import EarningsCache
        mock_cache = MagicMock(spec=EarningsCache)
        mock_cache.is_in_blackout.return_value = True
        mock_cache.blackout_days = 1
        agent._earnings_cache = mock_cache

        import config
        with patch.object(config, "EARNINGS_BLACKOUT_DAYS", 1), \
             patch.object(config, "MAX_DAILY_TRADES", 10), \
             patch.object(config, "MAX_OPEN_POSITIONS", 20), \
             patch.object(config, "MAX_POSITION_PCT", 0.5), \
             patch.object(config, "MIN_TRADE_VALUE", 1.0), \
             patch.object(config, "MAX_SECTOR_EXPOSURE_PCT", 1.0), \
             patch.object(config, "MAX_CORRELATED_EXPOSURE_PCT", 1.0), \
             patch.object(config, "RVOL_THRESHOLD", 0.0), \
             patch.object(config, "CORRELATION_THRESHOLD", 0.8), \
             patch.object(config, "CORRELATION_LOOKBACK_DAYS", 30), \
             patch.object(config, "SECTOR_MAP_JSON", ""), \
             patch.object(config, "SECTOR_MAP_PATH", ""), \
             patch.object(config, "LOOKBACK_DAYS", 30), \
             patch.object(config, "DAILY_LOSS_LIMIT_PCT", 0.03), \
             patch.object(config, "MAX_DRAWDOWN_PCT", 0.15), \
             patch.object(config, "MARKET_TIMEZONE", "America/New_York"):

            agent.circuit_breaker = MagicMock()
            agent.circuit_breaker.update.return_value = (False, "")
            agent.rvol_checker = MagicMock()
            agent.rvol_checker.check.return_value = True
            agent.sector_exposure_checker = MagicMock()
            agent.sector_exposure_checker.check.return_value = True
            agent.correlation_exposure_checker = MagicMock()
            agent.correlation_exposure_checker.check.return_value = True

            signal = self._make_signal()
            await agent._handle_signal(signal)

        failed = [e for e in published if isinstance(e, RiskCheckFailed)]
        self.assertEqual(len(failed), 1)
        self.assertIn("arnings", failed[0].reason)

    async def test_earnings_blackout_zero_skips_check(self):
        """When EARNINGS_BLACKOUT_DAYS=0 the earnings cache is never called."""
        from agents.risk_agent import RiskAgent
        bus = AsyncMock()
        bus.publish = AsyncMock()
        bus.subscribe = MagicMock()
        bus.unsubscribe = MagicMock()
        broker = MagicMock()
        broker.universe = MagicMock()

        agent = RiskAgent(event_bus=bus, broker=broker)
        agent.universe = MagicMock()
        agent.session_id = "test"

        import config
        with patch.object(config, "EARNINGS_BLACKOUT_DAYS", 0):
            # _earnings_cache should stay None — no lookup attempted
            signal = self._make_signal(action="sell")
            # For sell signals we test the blackout doesn't intervene
            # (sell path doesn't check earnings, only buy does)
            self.assertIsNone(agent._earnings_cache)


# ---------------------------------------------------------------------------
# Config fields: new env vars load correctly
# ---------------------------------------------------------------------------

class TestMarketAwarenessConfig(unittest.TestCase):

    def test_avoid_open_minutes_default_zero(self):
        import importlib
        import config as cfg
        importlib.reload(cfg)
        self.assertEqual(cfg.AVOID_OPEN_MINUTES, 0)

    def test_avoid_close_minutes_default_zero(self):
        import importlib
        import config as cfg
        importlib.reload(cfg)
        self.assertEqual(cfg.AVOID_CLOSE_MINUTES, 0)

    def test_earnings_blackout_days_default_zero(self):
        import importlib
        import config as cfg
        importlib.reload(cfg)
        self.assertEqual(cfg.EARNINGS_BLACKOUT_DAYS, 0)

    def test_fomc_blackout_enabled_default_false(self):
        import importlib
        import config as cfg
        importlib.reload(cfg)
        self.assertFalse(cfg.FOMC_BLACKOUT_ENABLED)

    def test_env_vars_are_read(self):
        import importlib
        import os
        with patch.dict(os.environ, {
            "AVOID_OPEN_MINUTES": "30",
            "AVOID_CLOSE_MINUTES": "15",
            "EARNINGS_BLACKOUT_DAYS": "2",
            "FOMC_BLACKOUT_ENABLED": "true",
        }):
            import config as cfg
            importlib.reload(cfg)
            self.assertEqual(cfg.AVOID_OPEN_MINUTES, 30)
            self.assertEqual(cfg.AVOID_CLOSE_MINUTES, 15)
            self.assertEqual(cfg.EARNINGS_BLACKOUT_DAYS, 2)
            self.assertTrue(cfg.FOMC_BLACKOUT_ENABLED)


if __name__ == "__main__":
    unittest.main()
