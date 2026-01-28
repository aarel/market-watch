"""Data Agent - fetches market data on schedule."""
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from .base import BaseAgent
from .events import MarketDataReady

if TYPE_CHECKING:
    from broker import AlpacaBroker
    from .event_bus import EventBus


def _snapshot_price(snapshot):
    if snapshot is None:
        return None
    latest_trade = getattr(snapshot, "latest_trade", None)
    if latest_trade and getattr(latest_trade, "price", None):
        return float(latest_trade.price)
    daily_bar = getattr(snapshot, "daily_bar", None)
    if daily_bar and getattr(daily_bar, "c", None):
        return float(daily_bar.c)
    minute_bar = getattr(snapshot, "minute_bar", None)
    if minute_bar and getattr(minute_bar, "c", None):
        return float(minute_bar.c)
    return None


def _snapshot_prev_close(snapshot):
    if snapshot is None:
        return None
    prev_bar = getattr(snapshot, "prev_daily_bar", None)
    if prev_bar and getattr(prev_bar, "c", None):
        return float(prev_bar.c)
    return None


class DataAgent(BaseAgent):
    """Fetches market data and emits MarketDataReady events."""

    def __init__(self, event_bus: "EventBus", broker: "AlpacaBroker", interval_minutes: int = 10):
        super().__init__("DataAgent", event_bus)
        self.broker = broker
        self.interval_minutes = interval_minutes
        self._cache = {}
        self._last_fetch = None

    async def start(self):
        """Start the data fetching loop."""
        await super().start()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the data fetching loop."""
        await super().stop()

    async def _run_loop(self):
        """Main loop that fetches data periodically."""
        while self.running:
            try:
                await self.fetch_data()
            except Exception as e:
                print(f"DataAgent error: {e}")

            await asyncio.sleep(self.interval_minutes * 60)

    async def fetch_data(self, symbols: list[str] = None):
        """Fetch market data for all symbols and emit event."""
        import config
        from screener import compute_top_gainers
        from screener_universe import get_universe

        # Check market status
        market_open = self.broker.is_market_open()

        top_gainers = self._cache.get("top_gainers", [])
        market_indices = self._cache.get("market_indices", [])
        if symbols is None and config.WATCHLIST_MODE == "top_gainers":
            try:
                universe = get_universe(config.TOP_GAINERS_UNIVERSE)
                snapshots = self.broker.get_snapshots(universe)
                top_gainers = compute_top_gainers(
                    snapshots,
                    min_price=config.TOP_GAINERS_MIN_PRICE,
                    min_volume=config.TOP_GAINERS_MIN_VOLUME,
                    limit=config.TOP_GAINERS_COUNT,
                )
            except Exception as e:
                print(f"DataAgent: Error computing top gainers: {e}")
            if top_gainers:
                symbols = [entry["symbol"] for entry in top_gainers]
                config.WATCHLIST = symbols
            else:
                symbols = config.WATCHLIST
        elif symbols is None:
            symbols = config.WATCHLIST

        # Ensure we always have something to process (avoid empty symbol list on failures)
        if not symbols:
            symbols = config.WATCHLIST or ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]

        # Market index proxies for UI ticker
        if config.MARKET_INDEX_SYMBOLS:
            try:
                index_snaps = self.broker.get_snapshots(config.MARKET_INDEX_SYMBOLS)
                market_indices = []
                for symbol in config.MARKET_INDEX_SYMBOLS:
                    snapshot = index_snaps.get(symbol)
                    price = _snapshot_price(snapshot)
                    prev_close = _snapshot_prev_close(snapshot)
                    if price is None or prev_close is None or prev_close <= 0:
                        continue
                    change_pct = (price - prev_close) / prev_close
                    market_indices.append({
                        "symbol": symbol,
                        "price": price,
                        "prev_close": prev_close,
                        "change_pct": change_pct,
                    })
            except Exception as e:
                print(f"DataAgent: Error computing market indices: {e}")

        # Fetch account info
        account = self.broker.get_account()
        account_data = {
            "portfolio_value": float(account.portfolio_value),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "equity": float(account.equity),
        }

        # Fetch positions
        positions = []
        held_symbols = set()
        try:
            for pos in self.broker.get_positions():
                positions.append({
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "market_value": float(pos.market_value),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc) * 100,
                })
                held_symbols.add(pos.symbol)
        except Exception as e:
            print(f"DataAgent: Error fetching positions: {e}")

        # Always monitor held symbols even if they drop out of top gainers
        symbols = list(set(symbols) | held_symbols)

        # Fetch prices and bars for each symbol
        prices = {entry["symbol"]: entry["price"] for entry in top_gainers if entry.get("price")}
        bars = {}

        for symbol in symbols:
            try:
                if symbol not in prices:
                    price = self.broker.get_current_price(symbol)
                    if price:
                        prices[symbol] = price

                symbol_bars = self.broker.get_bars(symbol, days=config.LOOKBACK_DAYS)
                if symbol_bars is not None and len(symbol_bars) > 0:
                    bars[symbol] = symbol_bars.to_dict()
            except Exception as e:
                print(f"DataAgent: Error fetching {symbol}: {e}")

        # Cache the data
        self._cache = {
            "prices": prices,
            "bars": bars,
            "account": account_data,
            "positions": positions,
            "top_gainers": top_gainers,
            "market_indices": market_indices,
            "market_open": market_open,
        }
        self._last_fetch = datetime.now()

        # Emit event
        event = MarketDataReady(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            symbols=symbols,
            prices=prices,
            bars=bars,
            account=account_data,
            positions=positions,
            top_gainers=top_gainers,
            market_indices=market_indices,
            market_open=market_open,
        )
        await self.event_bus.publish(event)

        return event

    def get_cached_data(self):
        """Get the most recent cached data."""
        return self._cache

    def status(self) -> dict:
        """Get agent status."""
        base = super().status()
        base["last_fetch"] = self._last_fetch.isoformat() if self._last_fetch else None
        base["cached_symbols"] = list(self._cache.get("prices", {}).keys())
        return base
