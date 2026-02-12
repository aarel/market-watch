"""Risk exposure checkers - modular risk validation components."""
import logging

logger = logging.getLogger(__name__)
import json
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from broker import AlpacaBroker


class SectorMapLoader:
    """Loads and caches sector map from JSON string or file."""

    def __init__(self):
        self._cache: dict | None = None
        self._cache_key: tuple | None = None

    def get(self, sector_map_json: str = "", sector_map_path: str = "") -> dict:
        """Load sector map with caching.

        Args:
            sector_map_json: JSON string mapping symbol->sector
            sector_map_path: Path to JSON file mapping symbol->sector

        Returns:
            Dictionary mapping symbol (uppercase) -> sector name
        """
        key = (sector_map_json, sector_map_path)
        if self._cache is not None and self._cache_key == key:
            return self._cache

        raw_map = {}
        if sector_map_json:
            try:
                raw_map = json.loads(sector_map_json)
            except Exception as e:
                logger.error(f"Error parsing SECTOR_MAP_JSON: {e}")
        elif sector_map_path:
            try:
                with open(sector_map_path, encoding="utf-8") as handle:
                    raw_map = json.load(handle)
            except FileNotFoundError:
                logger.warning(f"Sector map file not found: {sector_map_path}")
            except Exception as e:
                logger.error(f"Error reading sector map: {e}")

        # Normalize keys to uppercase
        normalized = {}
        if isinstance(raw_map, dict):
            for key_sym, value in raw_map.items():
                if not key_sym or not value:
                    continue
                normalized[str(key_sym).upper()] = str(value).strip()
        else:
            logger.error("Sector map must be a JSON object of symbol->sector")

        self._cache = normalized
        self._cache_key = key
        return normalized


class ReturnCalculator:
    """Calculates price returns for correlation analysis."""

    def __init__(self, broker: "AlpacaBroker"):
        self.broker = broker

    def get_returns(self, symbol: str, lookback_days: int) -> pd.Series | None:
        """Calculate daily returns for a symbol.

        Args:
            symbol: Stock symbol
            lookback_days: Number of days to look back

        Returns:
            Pandas Series of daily returns, or None if data unavailable
        """
        try:
            bars = self.broker.get_bars(symbol, days=lookback_days)
        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return None

        if bars is None or len(bars) == 0:
            return None

        try:
            closes = bars["close"]
        except Exception:
            return None

        if closes is None or len(closes) < 3:
            return None

        returns = closes.pct_change().dropna()
        if returns is None or len(returns) < 2:
            return None

        # Ensure we return a Series, not DataFrame
        if isinstance(returns, pd.DataFrame):
            returns = returns.iloc[:, 0]

        return returns


class SectorExposureChecker:
    """Checks if a trade would violate sector exposure limits."""

    def __init__(self, sector_map_loader: SectorMapLoader):
        self.sector_map_loader = sector_map_loader

    def check(
        self,
        symbol: str,
        trade_value: float,
        positions,
        portfolio_value: float,
        max_sector_exposure_pct: float,
        sector_map_json: str = "",
        sector_map_path: str = "",
    ) -> bool:
        """Check if adding this trade would exceed sector exposure limit.

        Args:
            symbol: Stock symbol to check
            trade_value: Dollar value of proposed trade
            positions: List of current positions
            portfolio_value: Total portfolio value
            max_sector_exposure_pct: Maximum allowed exposure (e.g., 0.30 for 30%)
            sector_map_json: JSON string mapping symbol->sector
            sector_map_path: Path to JSON file mapping symbol->sector

        Returns:
            True if trade is allowed, False if it would violate limit
        """
        if portfolio_value <= 0:
            return True

        sector_map = self.sector_map_loader.get(sector_map_json, sector_map_path)
        if not sector_map:
            return True

        symbol_upper = symbol.upper()
        sector = sector_map.get(symbol_upper)
        if not sector:
            return True

        # Calculate current sector exposure
        sector_value = 0.0
        for position in positions:
            pos_symbol = getattr(position, "symbol", None)
            if not pos_symbol:
                continue
            pos_sector = sector_map.get(str(pos_symbol).upper())
            if pos_sector != sector:
                continue
            sector_value += self._get_position_value(position)

        # Check proposed exposure
        proposed_value = sector_value + max(trade_value, 0.0)
        exposure_pct = proposed_value / portfolio_value
        return exposure_pct <= max_sector_exposure_pct

    @staticmethod
    def _get_position_value(position) -> float:
        """Extract market value from position object."""
        value = getattr(position, "market_value", 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class CorrelationExposureChecker:
    """Checks if a trade would violate correlation exposure limits."""

    def __init__(self, return_calculator: ReturnCalculator):
        self.return_calculator = return_calculator

    def check(
        self,
        symbol: str,
        trade_value: float,
        positions,
        portfolio_value: float,
        max_correlated_exposure_pct: float,
        correlation_threshold: float,
        lookback_days: int,
    ) -> bool:
        """Check if adding this trade would exceed correlated exposure limit.

        Args:
            symbol: Stock symbol to check
            trade_value: Dollar value of proposed trade
            positions: List of current positions
            portfolio_value: Total portfolio value
            max_correlated_exposure_pct: Maximum allowed exposure (e.g., 0.40 for 40%)
            correlation_threshold: Correlation above this is considered "correlated"
            lookback_days: Days of history to use for correlation

        Returns:
            True if trade is allowed, False if it would violate limit
        """
        if portfolio_value <= 0:
            return True
        if not positions:
            return True

        target_returns = self.return_calculator.get_returns(symbol, lookback_days)
        if target_returns is None or target_returns.empty:
            return True

        correlated_value = 0.0
        target_existing_value = 0.0
        symbol_upper = symbol.upper()

        for position in positions:
            pos_symbol = getattr(position, "symbol", None)
            if not pos_symbol:
                continue
            pos_symbol = str(pos_symbol).upper()
            pos_value = self._get_position_value(position)

            # Track existing position in target symbol
            if pos_symbol == symbol_upper:
                target_existing_value += pos_value
                continue

            # Calculate correlation with this position
            pos_returns = self.return_calculator.get_returns(pos_symbol, lookback_days)
            if pos_returns is None or pos_returns.empty:
                continue

            aligned = target_returns.align(pos_returns, join="inner")
            if len(aligned[0]) < 3 or len(aligned[1]) < 3:
                continue

            corr = aligned[0].corr(aligned[1])
            if corr is None:
                continue
            if corr >= correlation_threshold:
                correlated_value += pos_value

        # Check proposed exposure (including existing position in same symbol)
        proposed_value = correlated_value + target_existing_value + max(trade_value, 0.0)
        exposure_pct = proposed_value / portfolio_value
        return exposure_pct <= max_correlated_exposure_pct

    @staticmethod
    def _get_position_value(position) -> float:
        """Extract market value from position object."""
        value = getattr(position, "market_value", 0.0)
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0


class RVOLChecker:
    """Checks if relative volume meets threshold (filters low-volume price moves)."""

    def __init__(self, broker: "AlpacaBroker"):
        self.broker = broker

    def check(self, symbol: str, rvol_threshold: float, lookback_days: int) -> bool:
        """Check if relative volume meets minimum threshold.

        RVOL = current_volume / 30-day_volume_sma

        Args:
            symbol: Stock symbol to check
            rvol_threshold: Minimum RVOL required (e.g., 2.0 means 2x average volume)
            lookback_days: Days to use for volume average

        Returns:
            True if RVOL >= threshold or if data unavailable (fail-open)
        """
        try:
            bars = self.broker.get_bars(symbol, days=lookback_days)
        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return True  # Allow trade if data unavailable

        if bars is None or len(bars) == 0:
            return True

        try:
            volumes = bars["volume"]
        except Exception:
            return True

        if volumes is None or len(volumes) < 2:
            return True

        # Calculate 30-day SMA of volume
        volume_sma = volumes.mean()
        if volume_sma <= 0:
            return True

        # Get current (most recent) volume
        current_volume = volumes.iloc[-1]
        if pd.isna(current_volume) or current_volume <= 0:
            return True

        # Calculate RVOL
        rvol = current_volume / volume_sma

        # Convert numpy bool to Python bool for consistent return type
        return bool(rvol >= rvol_threshold)
