"""
Fake Broker for simulation mode.

This class mimics the AlpacaBroker interface but uses an in-memory portfolio
and generates fake price data, allowing the bot to be tested 24/7 without
connecting to a real brokerage or requiring a live market.
"""
import random
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path
import pandas as pd
import numpy as np

import config
from universe import Universe


class FakeBroker:
    """
    A fake broker that simulates a trading environment.
    - Manages an in-memory account and positions.
    - Generates fluctuating price data for assets.
    - Logs trades instead of executing them.
    - Always reports the market as 'open'.
    """

    def __init__(self, universe: Universe = None):
        """
        Initialize FakeBroker.

        Args:
            universe: Execution universe (should always be SIMULATION). If None, defaults to SIMULATION.
        """
        # Default to SIMULATION if not specified
        if universe is None:
            universe = Universe.SIMULATION

        # Validate universe (FakeBroker should only be SIMULATION)
        if universe != Universe.SIMULATION:
            raise ValueError(
                f"FakeBroker should only operate in SIMULATION universe. "
                f"Got: {universe.value}. Use AlpacaBroker for LIVE/PAPER."
            )

        self.universe = universe
        # In-memory storage
        self._account = {
            "portfolio_value": 100000.0,
            "cash": 100000.0,
            "buying_power": 100000.0,
            "equity": 100000.0,
        }
        self._positions = {}  # symbol -> SimpleNamespace(qty, avg_entry_price, market_value, etc.)
        self._orders = {}     # order_id -> SimpleNamespace(...)
        self._prices = {}     # symbol -> price
        self._assets = {}     # symbol -> SimpleNamespace(name, ...)
        self._asset_name_cache = {}
        self._alpaca_client = self._try_init_alpaca()
        self._replay_mode = config.SIM_REPLAY_ENABLED
        self._replay_date = config.SIM_REPLAY_DATE or datetime.now(timezone.utc).date().strftime("%Y%m%d")
        self._replay_frames = {}  # symbol -> DataFrame
        self._replay_idx = {}     # symbol -> int

        # Seed initial prices for default watchlist
        for symbol in config.WATCHLIST:
            self._prices[symbol] = self._seed_price(symbol)
            asset = SimpleNamespace(name=f"{symbol.upper()} Inc.", tradable=True, shortable=True, status='active')
            self._assets[symbol] = asset

        self._validate_connection()
        if self._replay_mode:
            self._load_replay_frames(config.WATCHLIST)

    def _try_init_alpaca(self):
        """Optionally initialize Alpaca client for name lookups."""
        try:
            import alpaca_trade_api as tradeapi
            if config.ALPACA_API_KEY and config.ALPACA_SECRET_KEY:
                return tradeapi.REST(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, base_url=config.get_alpaca_url())
        except Exception as exc:
            print(f"FakeBroker: Alpaca lookup disabled ({exc})")
        return None

    def _validate_connection(self):
        """Prints a success message for simulation mode."""
        print(f"Connected to FakeBroker ({self.universe.value} universe)")
        print(f"Initial portfolio value: ${self._account['portfolio_value']:.2f}")

    def _seed_price(self, symbol: str) -> float:
        """Seed a starting price, preferring Alpaca data when available."""
        if self._alpaca_client:
            try:
                trade = self._alpaca_client.get_last_trade(symbol)
                if trade and getattr(trade, "price", None):
                    return max(0.01, float(trade.price))
            except Exception:
                pass
            try:
                quote = self._alpaca_client.get_last_quote(symbol)
                if quote and getattr(quote, "askprice", None):
                    return max(0.01, float(quote.askprice))
            except Exception:
                pass
        return round(random.uniform(10, 300), 2)

    def _load_replay_frames(self, symbols):
        """Load replay CSVs if available."""
        for sym in symbols:
            path = Path("data/replay") / f"{sym}-{self._replay_date}.csv"
            if path.exists():
                try:
                    df = pd.read_csv(path, parse_dates=["timestamp"])
                    if not df.empty:
                        self._replay_frames[sym] = df
                        self._replay_idx[sym] = 0
                        # seed price from first row
                        self._prices[sym] = float(df.iloc[0]["close"])
                        print(f"Replay loaded for {sym} ({len(df)} bars)")
                except Exception as exc:
                    print(f"Replay load failed for {sym}: {exc}")

    def _replay_step(self, symbol: str):
        """Advance one replay tick for symbol, return price if available."""
        df = self._replay_frames.get(symbol)
        if df is None or df.empty:
            return None
        idx = self._replay_idx.get(symbol, 0)
        row = df.iloc[idx % len(df)]
        self._replay_idx[symbol] = (idx + 1) % len(df)
        price = float(row["close"])
        self._prices[symbol] = price
        return price

    def _jiggle_prices(self):
        """Apply a random fluctuation to all tracked prices."""
        for symbol, price in self._prices.items():
            if self._replay_mode and symbol in self._replay_frames:
                replay_price = self._replay_step(symbol)
                if replay_price is not None:
                    continue  # already set from replay
            factor = config.SIMULATION_JIGGLE_FACTOR
            new_price = price * (1 + random.uniform(-factor, factor))
            self._prices[symbol] = max(0.01, new_price) # Prevent price from going to zero

    def _update_portfolio(self):
        """Recalculate portfolio value based on current prices."""
        position_value = 0
        for symbol, pos in self._positions.items():
            current_price = self._prices.get(symbol, pos.avg_entry_price)
            pos.market_value = float(pos.qty) * current_price
            pos.unrealized_pl = (current_price - float(pos.avg_entry_price)) * float(pos.qty)
            if float(pos.avg_entry_price) > 0:
                pos.unrealized_plpc = (current_price / float(pos.avg_entry_price)) - 1
            else:
                pos.unrealized_plpc = 0.0
            position_value += pos.market_value

        self._account["equity"] = self._account["cash"] + position_value
        self._account["portfolio_value"] = self._account["equity"]


    # --- Public API Methods ---

    def get_account(self):
        """Get the simulated account information."""
        self._update_portfolio()
        return SimpleNamespace(**self._account)

    def get_buying_power(self):
        """Get available buying power."""
        return self._account["buying_power"]

    def get_portfolio_value(self):
        """Get total portfolio value."""
        self._update_portfolio()
        return self._account["portfolio_value"]

    def get_positions(self):
        """Get all current simulated positions."""
        self._update_portfolio()
        return list(self._positions.values())

    def get_position(self, symbol):
        """Get a position for a specific symbol."""
        self._update_portfolio()
        return self._positions.get(symbol, None)

    def get_bars(self, symbol, days=20):
        """Generate plausible-looking historical bars."""
        if self._replay_mode and symbol in self._replay_frames:
            df = self._replay_frames[symbol].copy()
            # return the last `days` rows as a DataFrame with proper index
            tail = df.tail(days)
            tail = tail.set_index(pd.to_datetime(tail["timestamp"]))
            return tail[["open", "high", "low", "close", "volume"]]

        if symbol not in self._prices:
             self._prices[symbol] = round(random.uniform(50, 500), 2)

        price = self._prices[symbol]
        dates = pd.to_datetime([datetime.now() - timedelta(days=i) for i in range(days)])
        # Create a simple random walk for the close price
        closes = [price]
        for _ in range(1, days):
            closes.append(closes[-1] * (1 + random.uniform(-0.02, 0.02)))
        closes.reverse()

        df = pd.DataFrame({
            "close": closes,
            "open": [c * random.uniform(0.98, 1.02) for c in closes],
            "high": [c * random.uniform(1.0, 1.03) for c in closes],
            "low": [c * random.uniform(0.97, 1.0) for c in closes],
            "volume": [random.randint(1_000_000, 10_000_000) for _ in range(days)]
        }, index=dates)
        return df


    def get_snapshots(self, symbols):
        """Get simulated snapshots for multiple symbols."""
        self._jiggle_prices()
        snapshots = {}
        for symbol in symbols:
            if symbol not in self._prices:
                 self._prices[symbol] = round(random.uniform(50, 500), 2)
            
            price = self._prices[symbol]
            prev_close = price * (1 + random.uniform(-0.05, 0.05))
            
            snapshots[symbol] = SimpleNamespace(
                latest_trade=SimpleNamespace(price=price),
                daily_bar=SimpleNamespace(c=price, v=random.randint(1_000_000, 10_000_000)),
                prev_daily_bar=SimpleNamespace(c=prev_close, v=random.randint(1_000_000, 10_000_000)),
                minute_bar=None,
            )
        return snapshots

    def get_current_price(self, symbol):
        """Get the current simulated price for a symbol."""
        self._jiggle_prices()
        if symbol not in self._prices:
            self._prices[symbol] = round(random.uniform(50, 500), 2)
        return self._prices.get(symbol)

    def submit_order(self, symbol, qty=None, notional=None, side="buy", client_order_id=None):
        """Simulate submitting a market order."""
        # Seed a price if missing to avoid None responses
        if symbol not in self._prices:
            self._prices[symbol] = round(random.uniform(20, 200), 2)

        price = self._prices[symbol]

        if notional:
            qty = float(notional) / price
        
        qty = float(qty)
        order_value = qty * price

        print(f"Simulating {side.upper()} order for {qty:.2f} shares of {symbol} @ ${price:.2f} (notional: ${order_value:.2f})")

        if side == "buy":
            if order_value > self._account["buying_power"]:
                print("SIMULATION: INSUFFICIENT BUYING POWER")
                return SimpleNamespace(
                    id=None,
                    symbol=symbol,
                    qty=qty,
                    side=side,
                    status="rejected",
                    rejected_reason="insufficient_buying_power",
                )
            
            self._account["cash"] -= order_value
            self._account["buying_power"] -= order_value

            existing_pos = self._positions.get(symbol)
            if existing_pos:
                new_qty = float(existing_pos.qty) + qty
                new_total_cost = (float(existing_pos.avg_entry_price) * float(existing_pos.qty)) + order_value
                existing_pos.avg_entry_price = new_total_cost / new_qty
                existing_pos.qty = new_qty
            else:
                self._positions[symbol] = SimpleNamespace(
                    symbol=symbol,
                    qty=qty,
                    avg_entry_price=price,
                    market_value=order_value,
                    unrealized_pl=0.0,
                    unrealized_plpc=0.0
                )

        elif side == "sell":
            existing_pos = self._positions.get(symbol)
            if not existing_pos or float(existing_pos.qty) < qty:
                print("SIMULATION: NOT ENOUGH SHARES TO SELL")
                return None
            
            self._account["cash"] += order_value
            self._account["buying_power"] += order_value
            
            if abs(float(existing_pos.qty) - qty) < 1e-6: # If selling all shares
                del self._positions[symbol]
            else:
                existing_pos.qty = float(existing_pos.qty) - qty


        order_id = str(uuid.uuid4())
        now = datetime.now()
        order = SimpleNamespace(
            id=order_id,
            symbol=symbol,
            qty=qty,
            side=side,
            status="filled",
            client_order_id=client_order_id,
            filled_avg_price=price,
            notional=order_value,
            submitted_at=now,
            filled_at=now,
            type="market",
            time_in_force="day",
        )
        self._orders[order_id] = order

        print(f"Simulated order {order_id} filled.")
        return order


    def is_market_open(self):
        """Approximate US market hours for SIM mode (NYSE 9:30-16:00 ET, weekdays)."""
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            now = datetime.now(timezone.utc)
        is_weekday = now.weekday() < 5
        minutes = now.hour * 60 + now.minute
        open_minutes = 9 * 60 + 30
        close_minutes = 16 * 60
        return is_weekday and open_minutes <= minutes <= close_minutes

    def get_next_market_open(self):
        """Returns a fake time."""
        return datetime.now() + timedelta(minutes=1)

    def get_next_market_close(self):
        """Returns a fake time."""
        return datetime.now() + timedelta(hours=1)
    
    def get_asset(self, symbol):
        """Gets a simulated asset."""
        return self._assets.get(symbol)

    def get_all_assets(self):
        """Gets all simulated assets."""
        return list(self._assets.values())

    def get_asset_names(self, symbols: list[str]) -> dict[str, str]:
        """Get company names for multiple symbols."""
        common = {
            "AAPL": "Apple Inc.",
            "MSFT": "Microsoft Corporation",
            "GOOG": "Alphabet Inc. (Class C)",
            "GOOGL": "Alphabet Inc. (Class A)",
            "AMZN": "Amazon.com, Inc.",
            "META": "Meta Platforms, Inc.",
            "NVDA": "NVIDIA Corporation",
            "TSLA": "Tesla, Inc.",
            "AMD": "Advanced Micro Devices, Inc.",
            "INTC": "Intel Corporation",
            "NFLX": "Netflix, Inc.",
            "QQQ": "Invesco QQQ Trust",
            "SPY": "SPDR S&P 500 ETF",
        }
        names = {}
        for symbol in symbols:
            if not symbol:
                continue
            if symbol in common:
                names[symbol] = common[symbol]
                continue
            # cache hit
            if symbol in self._asset_name_cache:
                names[symbol] = self._asset_name_cache[symbol]
                continue
            # alpaca lookup if available
            if self._alpaca_client:
                try:
                    asset = self._alpaca_client.get_asset(symbol)
                    if asset and getattr(asset, "name", None):
                        names[symbol] = asset.name
                        self._asset_name_cache[symbol] = asset.name
                        continue
                except Exception:
                    pass
            asset = self.get_asset(symbol)
            if asset and hasattr(asset, "name"):
                names[symbol] = asset.name
            elif symbol:
                names[symbol] = f"{symbol} Inc."
                self._asset_name_cache[symbol] = names[symbol]
        return names

    def list_orders(self, status="all", limit=50, after=None, until=None, direction="desc"):
        """List simulated orders."""
        # This is a simplified implementation. A real one would handle pagination/filtering.
        orders = sorted(self._orders.values(), key=lambda o: o.id, reverse=True)
        return orders[:limit]

    def list_all_orders(self, status="all"):
        """Fetch all simulated orders."""
        return self.list_orders(status=status, limit=500)
