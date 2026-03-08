"""Abstract broker interface.

All broker implementations must inherit from BaseBroker and implement
every abstract method. This enforces a consistent interface across
Alpaca, Interactive Brokers, and any future integrations, and enables
type-safe dependency injection in agents and the server.

Universe isolation rules (enforced in each concrete class):
  - AlpacaBroker → LIVE or PAPER only
  - IBKRBroker   → LIVE or PAPER only
  - FakeBroker   → SIMULATION only
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseBroker(ABC):
    """Abstract base class for all broker integrations.

    Concrete implementations must provide all abstract methods below.
    Methods whose signature carries defaults (e.g. days=20) may keep
    those defaults; the base class only declares the required names.
    """

    # ------------------------------------------------------------------
    # Account & portfolio
    # ------------------------------------------------------------------

    @abstractmethod
    def get_account(self):
        """Return account information (cash, buying_power, portfolio_value, etc.)."""

    @abstractmethod
    def get_buying_power(self) -> float:
        """Return the current available buying power in dollars."""

    @abstractmethod
    def get_portfolio_value(self) -> float:
        """Return the current total portfolio value (cash + positions)."""

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    @abstractmethod
    def get_positions(self) -> list:
        """Return all current open positions."""

    @abstractmethod
    def get_position(self, symbol: str):
        """Return the position for *symbol*, or None if not held."""

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    @abstractmethod
    def get_bars(self, symbol: str, days: int = 20):
        """Return a DataFrame of historical daily OHLCV bars for *symbol*."""

    @abstractmethod
    def get_snapshots(self, symbols: list[str]) -> dict:
        """Return latest snapshot data keyed by symbol."""

    @abstractmethod
    def get_current_price(self, symbol: str):
        """Return the latest trade price for *symbol*, or None on failure."""

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        qty=None,
        notional=None,
        side: str = "buy",
        client_order_id=None,
    ):
        """Submit a market order. Returns an order object or None on failure."""

    @abstractmethod
    def list_orders(
        self,
        status: str = "all",
        limit: int = 50,
        after=None,
        until=None,
        direction: str = "desc",
    ) -> list:
        """Return a list of orders matching the given filters."""

    @abstractmethod
    def list_all_orders(self, status: str = "all") -> list:
        """Return all orders (handling pagination internally)."""

    # ------------------------------------------------------------------
    # Market hours
    # ------------------------------------------------------------------

    @abstractmethod
    def is_market_open(self) -> bool:
        """Return True if the market is currently open."""

    @abstractmethod
    def get_next_market_open(self):
        """Return the next market open time."""

    @abstractmethod
    def get_next_market_close(self):
        """Return the next market close time."""

    # ------------------------------------------------------------------
    # Asset metadata
    # ------------------------------------------------------------------

    @abstractmethod
    def get_asset_names(self, symbols: list[str]) -> dict[str, str]:
        """Return a mapping of symbol → company name for the given symbols."""
