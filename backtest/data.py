"""
Historical data management for backtesting.

Handles downloading, caching, and loading of historical OHLCV data
from Alpaca's Market Data API.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

import config

# Only import alpaca if we have credentials
try:
    import alpaca_trade_api as tradeapi
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


class HistoricalData:
    """
    Manages historical price data for backtesting.

    Data is cached locally as CSV files to avoid repeated API calls.
    The cache directory structure is:
        data/historical/{symbol}_daily.csv

    Each CSV contains: timestamp, open, high, low, close, volume
    """

    DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data" / "historical"

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the historical data manager.

        Args:
            data_dir: Directory for cached data files.
                     Defaults to data/historical/
        """
        self.data_dir = Path(data_dir) if data_dir else self.DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Loaded data: symbol -> DataFrame
        self._data: dict[str, pd.DataFrame] = {}

        # Alpaca client (lazy initialization)
        self._api = None

    @property
    def api(self):
        """Lazy-load Alpaca API client."""
        if self._api is None:
            if not ALPACA_AVAILABLE:
                raise ImportError(
                    "alpaca-trade-api is not installed. "
                    "Install it with: pip install alpaca-trade-api"
                )
            if not config.ALPACA_API_KEY or not config.ALPACA_SECRET_KEY:
                raise ValueError(
                    "Alpaca API credentials not configured. "
                    "Set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables."
                )
            self._api = tradeapi.REST(
                config.ALPACA_API_KEY,
                config.ALPACA_SECRET_KEY,
                config.get_alpaca_url(),
                api_version='v2'
            )
        return self._api

    def _cache_path(self, symbol: str) -> Path:
        """Get the cache file path for a symbol."""
        return self.data_dir / f"{symbol.upper()}_daily.csv"

    def _load_cache(self, symbol: str) -> Optional[pd.DataFrame]:
        """Load cached data for a symbol if it exists."""
        cache_path = self._cache_path(symbol)
        if not cache_path.exists():
            return None

        try:
            df = pd.read_csv(
                cache_path,
                index_col='timestamp',
                parse_dates=True
            )
            return df
        except Exception as e:
            print(f"Warning: Could not load cache for {symbol}: {e}")
            return None

    def _save_cache(self, symbol: str, df: pd.DataFrame):
        """Save data to cache file."""
        cache_path = self._cache_path(symbol)
        df.to_csv(cache_path)
        print(f"Cached {len(df)} bars for {symbol} -> {cache_path}")

    def download(
        self,
        symbols: list[str],
        start: str,
        end: Optional[str] = None,
        force: bool = False
    ) -> dict[str, pd.DataFrame]:
        """
        Download historical data from Alpaca and cache locally.

        Args:
            symbols: List of ticker symbols to download
            start: Start date in YYYY-MM-DD format
            end: End date in YYYY-MM-DD format (defaults to today)
            force: If True, re-download even if cached data exists

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        if end is None:
            end = datetime.now().strftime('%Y-%m-%d')

        results = {}

        for symbol in symbols:
            symbol = symbol.upper()

            # Check cache first (unless force refresh)
            if not force:
                cached = self._load_cache(symbol)
                if cached is not None:
                    # Check if cache covers requested range
                    cache_start = cached.index.min().strftime('%Y-%m-%d')
                    cache_end = cached.index.max().strftime('%Y-%m-%d')

                    if cache_start <= start and cache_end >= end:
                        print(f"Using cached data for {symbol} ({cache_start} to {cache_end})")
                        results[symbol] = cached
                        self._data[symbol] = cached
                        continue

            # Download from Alpaca
            print(f"Downloading {symbol} from {start} to {end}...")
            try:
                bars = self.api.get_bars(
                    symbol,
                    tradeapi.TimeFrame.Day,
                    start=start,
                    end=end,
                    adjustment='all',  # Adjust for splits and dividends
                    feed=config.DATA_FEED
                ).df

                if bars.empty:
                    print(f"Warning: No data returned for {symbol}")
                    continue

                # Ensure timezone-naive index for consistency
                if bars.index.tz is not None:
                    bars.index = bars.index.tz_localize(None)

                # Cache the data
                self._save_cache(symbol, bars)

                results[symbol] = bars
                self._data[symbol] = bars

            except Exception as e:
                print(f"Error downloading {symbol}: {e}")
                continue

        return results

    def load(
        self,
        symbols: list[str],
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> dict[str, pd.DataFrame]:
        """
        Load historical data from cache.

        Args:
            symbols: List of ticker symbols to load
            start: Optional start date filter (YYYY-MM-DD)
            end: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dictionary mapping symbols to DataFrames
        """
        results = {}

        for symbol in symbols:
            symbol = symbol.upper()

            # Check if already loaded
            if symbol in self._data:
                df = self._data[symbol]
            else:
                # Try to load from cache
                df = self._load_cache(symbol)
                if df is None:
                    print(f"Warning: No cached data for {symbol}. Run download() first.")
                    continue
                self._data[symbol] = df

            # Apply date filters
            if start or end:
                mask = pd.Series(True, index=df.index)
                if start:
                    mask &= df.index >= pd.Timestamp(start)
                if end:
                    mask &= df.index <= pd.Timestamp(end)
                df = df[mask]

            results[symbol] = df

        return results

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get loaded data for a single symbol."""
        return self._data.get(symbol.upper())

    def get_price(self, symbol: str, date: pd.Timestamp, price_type: str = 'close') -> Optional[float]:
        """
        Get a specific price for a symbol on a date.

        Args:
            symbol: Ticker symbol
            date: Date to get price for
            price_type: 'open', 'high', 'low', 'close', or 'vwap'

        Returns:
            Price value or None if not available
        """
        df = self.get(symbol)
        if df is None:
            return None

        # Find the date in the index (handle exact match or nearest)
        try:
            if date in df.index:
                return float(df.loc[date, price_type])

            # Find nearest date (for weekends/holidays)
            mask = df.index <= date
            if not mask.any():
                return None
            nearest_date = df.index[mask][-1]
            return float(df.loc[nearest_date, price_type])
        except (KeyError, IndexError):
            return None

    def get_bars_up_to(
        self,
        symbol: str,
        date: pd.Timestamp,
        num_bars: int
    ) -> Optional[pd.DataFrame]:
        """
        Get historical bars up to and including a specific date.

        This is the key method for backtesting - it returns only data
        that would have been available at the given date (no lookahead).

        Args:
            symbol: Ticker symbol
            date: The current date in the backtest
            num_bars: Number of bars to return

        Returns:
            DataFrame with the requested bars, or None if insufficient data
        """
        df = self.get(symbol)
        if df is None:
            return None

        # Get all data up to and including the date
        mask = df.index <= date
        available = df[mask]

        if len(available) < num_bars:
            return None

        return available.tail(num_bars)

    @property
    def symbols(self) -> list[str]:
        """Get list of loaded symbols."""
        return list(self._data.keys())

    @property
    def date_range(self) -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        """Get the overall date range of loaded data."""
        if not self._data:
            return None, None

        all_dates = pd.DatetimeIndex([])
        for df in self._data.values():
            all_dates = all_dates.union(df.index)

        return all_dates.min(), all_dates.max()

    def list_cached(self) -> list[str]:
        """List all symbols with cached data."""
        cached = []
        for path in self.data_dir.glob("*_daily.csv"):
            symbol = path.stem.replace("_daily", "")
            cached.append(symbol)
        return sorted(cached)

    def clear_cache(self, symbols: Optional[list[str]] = None):
        """
        Clear cached data.

        Args:
            symbols: Specific symbols to clear, or None to clear all
        """
        if symbols is None:
            # Clear all
            for path in self.data_dir.glob("*_daily.csv"):
                path.unlink()
                print(f"Deleted {path}")
            self._data.clear()
        else:
            for symbol in symbols:
                cache_path = self._cache_path(symbol)
                if cache_path.exists():
                    cache_path.unlink()
                    print(f"Deleted cache for {symbol}")
                self._data.pop(symbol.upper(), None)

    def info(self) -> str:
        """Get summary information about loaded data."""
        lines = ["Historical Data Summary", "=" * 40]

        if not self._data:
            lines.append("No data loaded")
            return "\n".join(lines)

        lines.append(f"Symbols: {len(self._data)}")

        for symbol, df in sorted(self._data.items()):
            start = df.index.min().strftime('%Y-%m-%d')
            end = df.index.max().strftime('%Y-%m-%d')
            lines.append(f"  {symbol}: {len(df)} bars ({start} to {end})")

        return "\n".join(lines)
