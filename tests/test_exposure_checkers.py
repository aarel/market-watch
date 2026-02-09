"""Unit tests for modular risk exposure checkers."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from risk.exposure_checkers import (
    SectorMapLoader,
    ReturnCalculator,
    SectorExposureChecker,
    CorrelationExposureChecker,
    RVOLChecker,
)


class TestSectorMapLoader(unittest.TestCase):
    """Test SectorMapLoader class."""

    def test_load_from_json_string(self):
        """Test loading sector map from JSON string."""
        loader = SectorMapLoader()
        json_str = '{"AAPL": "Technology", "JPM": "Financial"}'

        sector_map = loader.get(sector_map_json=json_str)

        assert sector_map == {"AAPL": "Technology", "JPM": "Financial"}

    def test_load_from_file(self):
        """Test loading sector map from file."""
        loader = SectorMapLoader()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"TSLA": "Automotive", "NVDA": "Technology"}, f)
            temp_path = f.name

        try:
            sector_map = loader.get(sector_map_path=temp_path)
            assert sector_map == {"TSLA": "Automotive", "NVDA": "Technology"}
        finally:
            Path(temp_path).unlink()

    def test_caching_works(self):
        """Test that sector map is cached and not reloaded."""
        loader = SectorMapLoader()
        json_str = '{"AAPL": "Technology"}'

        # First call
        sector_map1 = loader.get(sector_map_json=json_str)
        # Second call with same params should return cached
        sector_map2 = loader.get(sector_map_json=json_str)

        assert sector_map1 is sector_map2  # Same object reference

    def test_uppercase_normalization(self):
        """Test that symbols are normalized to uppercase."""
        loader = SectorMapLoader()
        json_str = '{"aapl": "Technology", "Jpm": "Financial"}'

        sector_map = loader.get(sector_map_json=json_str)

        assert "AAPL" in sector_map
        assert "JPM" in sector_map
        assert "aapl" not in sector_map

    def test_invalid_json_returns_empty(self):
        """Test that invalid JSON returns empty dict."""
        loader = SectorMapLoader()
        json_str = '{invalid json}'

        sector_map = loader.get(sector_map_json=json_str)

        assert sector_map == {}

    def test_missing_file_returns_empty(self):
        """Test that missing file returns empty dict."""
        loader = SectorMapLoader()

        sector_map = loader.get(sector_map_path="/nonexistent/path.json")

        assert sector_map == {}

    def test_json_string_takes_precedence(self):
        """Test that JSON string takes precedence over file path."""
        loader = SectorMapLoader()
        json_str = '{"AAPL": "Technology"}'

        sector_map = loader.get(sector_map_json=json_str, sector_map_path="/some/path.json")

        assert sector_map == {"AAPL": "Technology"}


class TestReturnCalculator(unittest.TestCase):
    """Test ReturnCalculator class."""

    def test_calculate_returns_success(self):
        """Test successful return calculation."""
        broker = Mock()
        bars = pd.DataFrame({
            'close': [100, 102, 101, 103, 105]
        })
        broker.get_bars.return_value = bars

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert returns is not None
        assert len(returns) == 4  # pct_change drops first value
        assert isinstance(returns, pd.Series)
        broker.get_bars.assert_called_once_with("AAPL", days=5)

    def test_returns_none_when_no_bars(self):
        """Test that None is returned when no bars available."""
        broker = Mock()
        broker.get_bars.return_value = None

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert returns is None

    def test_returns_none_when_bars_empty(self):
        """Test that None is returned when bars is empty."""
        broker = Mock()
        broker.get_bars.return_value = pd.DataFrame()

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert returns is None

    def test_returns_none_when_insufficient_data(self):
        """Test that None is returned with insufficient data (<3 bars)."""
        broker = Mock()
        bars = pd.DataFrame({'close': [100, 102]})
        broker.get_bars.return_value = bars

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert returns is None

    def test_handles_broker_exception(self):
        """Test that broker exceptions are handled gracefully."""
        broker = Mock()
        broker.get_bars.side_effect = Exception("API error")

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert returns is None

    def test_converts_dataframe_to_series(self):
        """Test that DataFrame returns are converted to Series."""
        broker = Mock()
        # Create DataFrame with multiple columns (edge case)
        bars = pd.DataFrame({
            'close': [100, 102, 101, 103]
        })
        broker.get_bars.return_value = bars

        calculator = ReturnCalculator(broker)
        returns = calculator.get_returns("AAPL", 5)

        assert isinstance(returns, pd.Series)


class TestSectorExposureChecker(unittest.TestCase):
    """Test SectorExposureChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.sector_map_loader = SectorMapLoader()
        self.checker = SectorExposureChecker(self.sector_map_loader)

        # Create mock positions
        self.positions = [
            SimpleNamespace(symbol="AAPL", market_value=10000),
            SimpleNamespace(symbol="MSFT", market_value=15000),
            SimpleNamespace(symbol="JPM", market_value=5000),
        ]

    def test_allows_trade_when_under_limit(self):
        """Test that trade is allowed when sector exposure under limit."""
        sector_map_json = '{"AAPL": "Tech", "MSFT": "Tech", "GOOGL": "Tech", "JPM": "Financial"}'

        # Portfolio: $100k, Tech sector: $25k (25%), adding $5k GOOGL = 30% (at limit)
        result = self.checker.check(
            symbol="GOOGL",
            trade_value=5000,
            positions=self.positions,
            portfolio_value=100000,
            max_sector_exposure_pct=0.30,
            sector_map_json=sector_map_json,
        )

        assert result is True

    def test_rejects_trade_when_exceeds_limit(self):
        """Test that trade is rejected when sector exposure exceeds limit."""
        sector_map_json = '{"AAPL": "Tech", "MSFT": "Tech", "GOOGL": "Tech", "JPM": "Financial"}'

        # Portfolio: $100k, Tech sector: $25k (25%), adding $10k GOOGL = 35% (over 30% limit)
        result = self.checker.check(
            symbol="GOOGL",
            trade_value=10000,
            positions=self.positions,
            portfolio_value=100000,
            max_sector_exposure_pct=0.30,
            sector_map_json=sector_map_json,
        )

        assert result is False

    def test_allows_trade_when_symbol_not_in_map(self):
        """Test that trade is allowed when symbol not in sector map."""
        sector_map_json = '{"AAPL": "Tech", "MSFT": "Tech", "JPM": "Financial"}'

        # UNKNOWN symbol not in map - should allow
        result = self.checker.check(
            symbol="UNKNOWN",
            trade_value=50000,
            positions=self.positions,
            portfolio_value=100000,
            max_sector_exposure_pct=0.30,
            sector_map_json=sector_map_json,
        )

        assert result is True

    def test_allows_trade_when_no_sector_map(self):
        """Test that trade is allowed when no sector map provided."""
        result = self.checker.check(
            symbol="AAPL",
            trade_value=50000,
            positions=self.positions,
            portfolio_value=100000,
            max_sector_exposure_pct=0.30,
        )

        assert result is True

    def test_allows_trade_when_portfolio_value_zero(self):
        """Test that trade is allowed when portfolio value is zero."""
        sector_map_json = '{"AAPL": "Tech"}'

        result = self.checker.check(
            symbol="AAPL",
            trade_value=10000,
            positions=self.positions,
            portfolio_value=0,
            max_sector_exposure_pct=0.30,
            sector_map_json=sector_map_json,
        )

        assert result is True

    def test_handles_positions_without_symbol(self):
        """Test that positions without symbol attribute are skipped."""
        bad_positions = [
            SimpleNamespace(market_value=10000),  # No symbol
            SimpleNamespace(symbol="AAPL", market_value=5000),
        ]
        sector_map_json = '{"AAPL": "Tech"}'

        # Should only count AAPL
        result = self.checker.check(
            symbol="AAPL",
            trade_value=20000,
            positions=bad_positions,
            portfolio_value=100000,
            max_sector_exposure_pct=0.30,
            sector_map_json=sector_map_json,
        )

        # 5000 existing + 20000 new = 25000 / 100000 = 25% (under 30%)
        assert result is True


class TestCorrelationExposureChecker(unittest.TestCase):
    """Test CorrelationExposureChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.broker = Mock()
        self.return_calculator = ReturnCalculator(self.broker)
        self.checker = CorrelationExposureChecker(self.return_calculator)

        self.positions = [
            SimpleNamespace(symbol="AAPL", market_value=10000),
            SimpleNamespace(symbol="MSFT", market_value=15000),
        ]

    def test_allows_trade_when_under_limit(self):
        """Test that trade is allowed when correlation exposure under limit."""
        # AAPL and GOOGL are highly correlated (0.8)
        aapl_returns = pd.Series([0.01, 0.02, -0.01, 0.015])
        googl_returns = pd.Series([0.012, 0.019, -0.009, 0.014])  # Correlation ~0.99
        msft_returns = pd.Series([-0.02, 0.01, 0.03, -0.01])  # Low correlation

        def get_bars_side_effect(symbol, days):
            if symbol == "GOOGL":
                return pd.DataFrame({'close': [100, 101, 103, 102, 103.5]})
            elif symbol == "AAPL":
                return pd.DataFrame({'close': [150, 151.5, 154.5, 153, 155]})
            elif symbol == "MSFT":
                return pd.DataFrame({'close': [200, 196, 198, 204, 202]})
            return None

        self.broker.get_bars.side_effect = get_bars_side_effect

        # Portfolio: $100k, AAPL: $10k, MSFT: $15k (low corr)
        # Adding $15k GOOGL (high corr with AAPL) = $25k correlated / $100k = 25% (under 40%)
        result = self.checker.check(
            symbol="GOOGL",
            trade_value=15000,
            positions=self.positions,
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is True

    def test_rejects_trade_when_exceeds_limit(self):
        """Test that trade is rejected when correlation exposure exceeds limit."""
        # Setup high correlation between GOOGL and both positions
        def get_bars_side_effect(symbol, days):
            # All highly correlated
            return pd.DataFrame({'close': [100, 101, 103, 102, 103.5]})

        self.broker.get_bars.side_effect = get_bars_side_effect

        # Portfolio: $100k, positions: $25k total, adding $30k
        # If all correlated: $55k / $100k = 55% (over 40% limit)
        result = self.checker.check(
            symbol="GOOGL",
            trade_value=30000,
            positions=self.positions,
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is False

    def test_allows_trade_when_no_positions(self):
        """Test that trade is allowed when no open positions."""
        result = self.checker.check(
            symbol="AAPL",
            trade_value=50000,
            positions=[],
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is True

    def test_allows_trade_when_target_returns_unavailable(self):
        """Test that trade is allowed when target symbol returns unavailable."""
        self.broker.get_bars.return_value = None

        result = self.checker.check(
            symbol="AAPL",
            trade_value=50000,
            positions=self.positions,
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is True

    def test_allows_trade_when_portfolio_value_zero(self):
        """Test that trade is allowed when portfolio value is zero."""
        result = self.checker.check(
            symbol="AAPL",
            trade_value=10000,
            positions=self.positions,
            portfolio_value=0,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is True

    def test_includes_existing_position_in_same_symbol(self):
        """Test that existing position in target symbol is included in exposure."""
        # Adding to existing AAPL position
        def get_bars_side_effect(symbol, days):
            return pd.DataFrame({'close': [100, 101, 103, 102, 103.5]})

        self.broker.get_bars.side_effect = get_bars_side_effect

        # Portfolio: $100k, AAPL: $10k existing, adding $35k more
        # Total AAPL exposure: $45k (45% > 40% limit)
        result = self.checker.check(
            symbol="AAPL",
            trade_value=35000,
            positions=self.positions,
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is False

    def test_skips_positions_with_insufficient_data(self):
        """Test that positions with insufficient return data are skipped."""
        def get_bars_side_effect(symbol, days):
            if symbol == "GOOGL":
                return pd.DataFrame({'close': [100, 101, 103, 102]})
            elif symbol == "AAPL":
                return pd.DataFrame({'close': [150, 151]})  # Only 2 bars - insufficient
            elif symbol == "MSFT":
                return pd.DataFrame({'close': [200, 201, 203, 202]})
            return None

        self.broker.get_bars.side_effect = get_bars_side_effect

        # AAPL should be skipped due to insufficient data
        result = self.checker.check(
            symbol="GOOGL",
            trade_value=10000,
            positions=self.positions,
            portfolio_value=100000,
            max_correlated_exposure_pct=0.40,
            correlation_threshold=0.7,
            lookback_days=30,
        )

        assert result is True


class TestRVOLChecker(unittest.TestCase):
    """Test RVOLChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.broker = Mock()
        self.checker = RVOLChecker(self.broker)

    def test_allows_trade_when_rvol_above_threshold(self):
        """Test that trade is allowed when RVOL >= threshold."""
        bars = pd.DataFrame({
            'volume': [1000, 1000, 1000, 1000, 3000]  # Mean = 1400, current = 3000
        })
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        # Average volume = 1400, current = 3000, RVOL = 3000/1400 = 2.14 >= 2.0
        assert result is True

    def test_rejects_trade_when_rvol_below_threshold(self):
        """Test that trade is rejected when RVOL < threshold."""
        bars = pd.DataFrame({
            'volume': [1000, 1100, 900, 1050, 1200]  # Last volume is only 1.07x average
        })
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        # Average = 1050, current = 1200, RVOL = 1.14 < 2.0
        assert result is False

    def test_allows_trade_when_bars_unavailable(self):
        """Test that trade is allowed when bars unavailable (fail-open)."""
        self.broker.get_bars.return_value = None

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        assert result is True

    def test_allows_trade_when_broker_raises_exception(self):
        """Test that trade is allowed when broker raises exception (fail-open)."""
        self.broker.get_bars.side_effect = Exception("API error")

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        assert result is True

    def test_allows_trade_when_insufficient_volume_data(self):
        """Test that trade is allowed with insufficient volume data."""
        bars = pd.DataFrame({'volume': [1000]})  # Only 1 bar
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        assert result is True

    def test_allows_trade_when_volume_sma_zero(self):
        """Test that trade is allowed when volume SMA is zero."""
        bars = pd.DataFrame({'volume': [0, 0, 0]})
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        assert result is True

    def test_allows_trade_when_current_volume_zero(self):
        """Test that trade is allowed when current volume is zero."""
        bars = pd.DataFrame({'volume': [1000, 1100, 0]})
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        assert result is True

    def test_rvol_calculation_correct(self):
        """Test that RVOL calculation is mathematically correct."""
        bars = pd.DataFrame({
            'volume': [1000, 1000, 1000, 1000, 3000]  # Mean = 1400, current = 3000
        })
        self.broker.get_bars.return_value = bars

        result = self.checker.check("AAPL", rvol_threshold=2.0, lookback_days=30)

        # RVOL = 3000 / 1400 = 2.14 >= 2.0
        assert result is True


if __name__ == '__main__':
    unittest.main()
