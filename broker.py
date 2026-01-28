"""Alpaca broker integration.

Alpaca has two APIs:
- Trading API: Orders, positions, account info
- Market Data API: Price bars, quotes, trades

Both use the same API keys. The alpaca-trade-api library handles both.
Free tier uses IEX data feed, paid tier uses SIP (full market data).
"""
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
from datetime import datetime, timedelta
import pandas as pd
import config
from universe import Universe


class AlpacaBroker:
    """Handles all interactions with Alpaca brokerage."""

    def __init__(self, universe: Universe = None):
        """
        Initialize Alpaca broker.

        Args:
            universe: Execution universe (LIVE or PAPER). If None, determined from config.
        """
        # Determine universe
        if universe is None:
            universe = Universe.PAPER if config.TRADING_MODE == "paper" else Universe.LIVE

        # Validate universe (Alpaca broker cannot be SIMULATION)
        if universe == Universe.SIMULATION:
            raise ValueError(
                "AlpacaBroker cannot operate in SIMULATION universe. "
                "Use FakeBroker for simulation mode."
            )

        self.universe = universe

        # Trading API client
        self.api = tradeapi.REST(
            config.ALPACA_API_KEY,
            config.ALPACA_SECRET_KEY,
            config.get_alpaca_url(),
            api_version='v2'
        )
        # Data feed: 'iex' (free) or 'sip' (paid subscription)
        self.data_feed = config.DATA_FEED
        self._asset_name_cache = {}
        self._validate_connection()

    def _validate_connection(self):
        """Verify API credentials work."""
        try:
            account = self.api.get_account()
            print(f"Connected to Alpaca ({self.universe.value} universe)")
            print(f"Account status: {account.status}")
            print(f"Buying power: ${float(account.buying_power):.2f}")
            print(f"Portfolio value: ${float(account.portfolio_value):.2f}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Alpaca: {e}")

    def get_account(self):
        """Get account information."""
        return self.api.get_account()

    def get_buying_power(self):
        """Get available buying power."""
        account = self.api.get_account()
        return float(account.buying_power)

    def get_portfolio_value(self):
        """Get total portfolio value."""
        account = self.api.get_account()
        return float(account.portfolio_value)

    def get_positions(self):
        """Get all current positions."""
        return self.api.list_positions()

    def get_position(self, symbol):
        """Get position for a specific symbol, or None if not held."""
        try:
            return self.api.get_position(symbol)
        except APIError as e:
            if getattr(e, "status_code", None) == 404:
                return None
            raise

    def get_bars(self, symbol, days=20):
        """Get historical price bars for momentum calculation.

        Uses Market Data API with configured data feed (iex/sip).
        """
        end = datetime.now()
        # Use a wider buffer so we reliably get N trading days (weekends/holidays).
        buffer_days = max(days * 3, days + 10)
        start = end - timedelta(days=buffer_days)

        bars = self.api.get_bars(
            symbol,
            tradeapi.TimeFrame.Day,
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d'),
            limit=days,
            feed=self.data_feed
        ).df

        return bars

    def get_snapshots(self, symbols):
        """Get snapshots for multiple symbols."""
        if not symbols:
            return {}

        snapshots = {}
        chunk_size = 200
        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i + chunk_size]
            data = self.api.get_snapshots(chunk, feed=self.data_feed)
            snapshots.update(data)
        return snapshots

    def get_current_price(self, symbol):
        """Get the current/latest price for a symbol.

        Uses Market Data API with configured data feed (iex/sip).
        """
        try:
            # Get latest trade price (more reliable than quote for current price)
            trade = self.api.get_latest_trade(symbol, feed=self.data_feed)
            return trade.price
        except Exception as e:
            print(f"Error getting price for {symbol}: {e}")
            # Fallback: try quote
            try:
                quote = self.api.get_latest_quote(symbol, feed=self.data_feed)
                price = quote.ask_price if quote.ask_price > 0 else quote.bid_price
                return price if price > 0 else None
            except:
                return None

    def submit_order(self, symbol, qty=None, notional=None, side="buy", client_order_id=None):
        """
        Submit a market order.

        Args:
            symbol: Stock ticker
            qty: Number of shares (can be fractional)
            notional: Dollar amount to trade (alternative to qty)
            side: "buy" or "sell"

        Returns:
            Order object or None on failure
        """
        order_params = {
            "symbol": symbol,
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        if client_order_id:
            order_params["client_order_id"] = client_order_id
        if notional is not None:
            order_params["notional"] = float(notional)
        else:
            order_params["qty"] = qty

        try:
            order = self.api.submit_order(**order_params)
            print(f"Order submitted: {side} {symbol} - Order ID: {order.id}")
            return order
        except Exception as e:
            # Propagate the reason so callers can surface it
            print(f"Order failed: {e}")
            raise

    def get_asset_name(self, symbol: str) -> str:
        """Get the company name for a symbol, cached for reuse."""
        if not symbol:
            return ""
        cached = self._asset_name_cache.get(symbol)
        if cached is not None:
            return cached
        try:
            asset = self.api.get_asset(symbol)
            name = getattr(asset, "name", "") or ""
        except Exception as e:
            print(f"Error fetching asset name for {symbol}: {e}")
            name = ""
        self._asset_name_cache[symbol] = name
        return name

    def get_asset_names(self, symbols: list[str]) -> dict[str, str]:
        """Get company names for multiple symbols."""
        names = {}
        for symbol in symbols:
            name = self.get_asset_name(symbol)
            if name:
                names[symbol] = name
        return names

    def list_orders(self, status="all", limit=50, after=None, until=None, direction="desc"):
        """List orders from Alpaca."""
        return self.api.list_orders(
            status=status,
            limit=limit,
            after=after,
            until=until,
            direction=direction,
        )

    def list_all_orders(self, status="all"):
        """Fetch all orders with pagination."""
        orders = []
        until = None
        while True:
            batch = self.list_orders(status=status, limit=500, until=until, direction="desc")
            if not batch:
                break
            orders.extend(batch)
            if len(batch) < 500:
                break
            last = batch[-1]
            try:
                until_ts = last.submitted_at - pd.Timedelta(microseconds=1)
                until = until_ts.isoformat()
            except Exception:
                break
        return orders

    def is_market_open(self):
        """Check if the market is currently open."""
        clock = self.api.get_clock()
        return clock.is_open

    def get_next_market_open(self):
        """Get the next market open time."""
        clock = self.api.get_clock()
        return clock.next_open

    def get_next_market_close(self):
        """Get the next market close time."""
        clock = self.api.get_clock()
        return clock.next_close
