"""Interactive Brokers (IBKR) broker stub.

This module provides a structured foundation for an Interactive Brokers
integration via the TWS API (ib_insync or the official ibapi library).

Current status: STUB — all trading and data methods raise NotImplementedError.
The constructor accepts and stores configuration but does NOT open a network
connection, making it safe to instantiate in any environment.

Setup requirements (when activating):
    1. Install TWS (Trader Workstation) or IB Gateway.
    2. Enable API access in TWS: File → Global Configuration → API → Settings.
       Set the port (default 7497 for paper, 7496 for live TWS; 4002/4001 for
       IB Gateway).
    3. pip install ib_insync   (recommended) or ibapi (official)
    4. Set env vars:
         IBKR_HOST=127.0.0.1
         IBKR_PORT=7497          # 7497=paper TWS, 7496=live TWS
         IBKR_CLIENT_ID=1        # unique integer per simultaneous connection

Configuration env vars (all optional with sensible defaults):
    IBKR_HOST        — TWS/Gateway hostname (default: 127.0.0.1)
    IBKR_PORT        — TWS/Gateway port (default: 7497)
    IBKR_CLIENT_ID   — connection client ID (default: 1)
    IBKR_ACCOUNT     — IB account code (e.g. DU123456); required for live
"""
from __future__ import annotations

import logging
import os

from brokers.base import BaseBroker
from universe import Universe

logger = logging.getLogger(__name__)

# Default TWS paper-trading port (7496 for live, 4001/4002 for IB Gateway)
_DEFAULT_PORT = 7497


class IBKRBroker(BaseBroker):
    """Interactive Brokers broker stub.

    Inherits from BaseBroker and declares all required abstract methods.
    Trading / data methods raise NotImplementedError until the ib_insync
    integration layer is implemented.

    Args:
        universe: LIVE or PAPER — SIMULATION is not supported.
        host:     TWS/Gateway host (default from IBKR_HOST env or 127.0.0.1).
        port:     TWS/Gateway port (default from IBKR_PORT env or 7497).
        client_id: Connection client ID (default from IBKR_CLIENT_ID env or 1).
        account:  IB account code (default from IBKR_ACCOUNT env).
    """

    def __init__(
        self,
        universe: Universe,
        host: str | None = None,
        port: int | None = None,
        client_id: int | None = None,
        account: str | None = None,
    ):
        if not isinstance(universe, Universe):
            raise TypeError("IBKRBroker requires a Universe enum")
        if universe == Universe.SIMULATION:
            raise ValueError(
                "IBKRBroker cannot operate in SIMULATION universe. "
                "Use FakeBroker for simulation mode."
            )

        self.universe = universe
        self.host = host or os.getenv("IBKR_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("IBKR_PORT", str(_DEFAULT_PORT)))
        self.client_id = client_id or int(os.getenv("IBKR_CLIENT_ID", "1"))
        self.account = account or os.getenv("IBKR_ACCOUNT", "")

        logger.info(
            f"IBKRBroker configured ({universe.value}): "
            f"{self.host}:{self.port} client_id={self.client_id}"
        )
        # NOTE: intentionally NOT connecting here — call connect() to open TWS link.

    def connect(self):
        """Open a connection to TWS/IB Gateway.

        Not yet implemented. When activating, use ib_insync:

            from ib_insync import IB
            self._ib = IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id)
        """
        raise NotImplementedError(
            "IBKRBroker.connect() is not yet implemented. "
            "Install ib_insync and implement the TWS connection here."
        )

    # ------------------------------------------------------------------
    # Account & portfolio
    # ------------------------------------------------------------------

    def get_account(self):
        raise NotImplementedError(
            "IBKRBroker.get_account() not yet implemented. "
            "Use ib.accountValues() or ib.accountSummary() via ib_insync."
        )

    def get_buying_power(self) -> float:
        raise NotImplementedError("IBKRBroker.get_buying_power() not yet implemented.")

    def get_portfolio_value(self) -> float:
        raise NotImplementedError("IBKRBroker.get_portfolio_value() not yet implemented.")

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> list:
        raise NotImplementedError(
            "IBKRBroker.get_positions() not yet implemented. "
            "Use ib.positions() via ib_insync."
        )

    def get_position(self, symbol: str):
        raise NotImplementedError("IBKRBroker.get_position() not yet implemented.")

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------

    def get_bars(self, symbol: str, days: int = 20):
        raise NotImplementedError(
            "IBKRBroker.get_bars() not yet implemented. "
            "Use ib.reqHistoricalData() with a Stock contract via ib_insync."
        )

    def get_snapshots(self, symbols: list[str]) -> dict:
        raise NotImplementedError(
            "IBKRBroker.get_snapshots() not yet implemented. "
            "Use ib.reqMktData() or ib.reqTickers() via ib_insync."
        )

    def get_current_price(self, symbol: str):
        raise NotImplementedError(
            "IBKRBroker.get_current_price() not yet implemented. "
            "Use ib.reqTickers() with a Stock contract via ib_insync."
        )

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def submit_order(
        self,
        symbol: str,
        qty=None,
        notional=None,
        side: str = "buy",
        client_order_id=None,
    ):
        raise NotImplementedError(
            "IBKRBroker.submit_order() not yet implemented. "
            "Use ib.placeOrder() with a MarketOrder via ib_insync."
        )

    def list_orders(
        self,
        status: str = "all",
        limit: int = 50,
        after=None,
        until=None,
        direction: str = "desc",
    ) -> list:
        raise NotImplementedError(
            "IBKRBroker.list_orders() not yet implemented. "
            "Use ib.reqOpenOrders() or ib.reqAllOpenOrders() via ib_insync."
        )

    def list_all_orders(self, status: str = "all") -> list:
        raise NotImplementedError("IBKRBroker.list_all_orders() not yet implemented.")

    # ------------------------------------------------------------------
    # Market hours
    # ------------------------------------------------------------------

    def is_market_open(self) -> bool:
        raise NotImplementedError(
            "IBKRBroker.is_market_open() not yet implemented. "
            "Use ib.reqContractDetails() with trading hours info, "
            "or fall back to a local market-hours check via zoneinfo."
        )

    def get_next_market_open(self):
        raise NotImplementedError("IBKRBroker.get_next_market_open() not yet implemented.")

    def get_next_market_close(self):
        raise NotImplementedError("IBKRBroker.get_next_market_close() not yet implemented.")

    # ------------------------------------------------------------------
    # Asset metadata
    # ------------------------------------------------------------------

    def get_asset_names(self, symbols: list[str]) -> dict[str, str]:
        raise NotImplementedError(
            "IBKRBroker.get_asset_names() not yet implemented. "
            "Use ib.reqContractDetails() with a Stock contract to get longName."
        )

    # ------------------------------------------------------------------
    # Capabilities metadata (static, always available)
    # ------------------------------------------------------------------

    @staticmethod
    def capabilities() -> dict:
        """Return a description of IBKR broker capabilities.

        This is always available even before connect() is called.
        """
        return {
            "broker": "Interactive Brokers",
            "status": "stub",
            "supported_universes": ["LIVE", "PAPER"],
            "asset_classes": ["equities", "options", "futures", "forex", "bonds", "funds"],
            "fractional_shares": False,
            "commission": "tiered or fixed (account-dependent)",
            "market_data": "Level I and II via TWS subscription",
            "api_library": "ib_insync (recommended) or ibapi",
            "paper_trading_port": 7497,
            "live_trading_port": 7496,
            "notes": (
                "Requires TWS or IB Gateway running locally. "
                "Set IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, IBKR_ACCOUNT env vars."
            ),
        }
