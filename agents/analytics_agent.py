"""Analytics Agent - captures equity snapshots and executed trades."""
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from .base import BaseAgent
from .events import MarketDataReady, OrderExecuted, Event
from analytics.store import AnalyticsStore

if TYPE_CHECKING:
    from .event_bus import EventBus
    from broker import AlpacaBroker


class AnalyticsAgent(BaseAgent):
    """Listens to events and persists analytics-friendly data."""

    def __init__(self, event_bus: "EventBus", broker: "AlpacaBroker", store: AnalyticsStore):
        super().__init__("AnalyticsAgent", event_bus)
        self.broker = broker
        self.store = store

    async def start(self):
        await super().start()
        self.event_bus.subscribe(MarketDataReady, self._handle_market_data)
        self.event_bus.subscribe(OrderExecuted, self._handle_order_executed)

    async def stop(self):
        self.event_bus.unsubscribe(MarketDataReady, self._handle_market_data)
        self.event_bus.unsubscribe(OrderExecuted, self._handle_order_executed)
        await super().stop()

    async def _handle_market_data(self, event: MarketDataReady):
        account = event.account or {}
        if not account:
            return
        snapshot = {
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "equity": account.get("equity"),
            "portfolio_value": account.get("portfolio_value"),
            "cash": account.get("cash"),
            "buying_power": account.get("buying_power"),
            "market_open": event.market_open,
        }
        self.store.record_equity(snapshot)

    async def _handle_order_executed(self, event: OrderExecuted):
        trade = {
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "order_id": event.order_id,
            "symbol": event.symbol,
            "side": event.action,
            "qty": event.qty,
            "filled_avg_price": event.filled_avg_price,
            "notional": event.notional,
            "status": event.status or "filled",
            "submitted_at": event.submitted_at,
            "filled_at": event.filled_at,
            "source": event.source,
            "time_in_force": event.time_in_force,
            "order_type": event.order_type,
        }
        # Backfill notional if missing and qty/price available
        if trade.get("notional") is None and trade.get("qty") and trade.get("filled_avg_price"):
            trade["notional"] = float(trade["qty"]) * float(trade["filled_avg_price"])
        self.store.record_trade(trade)
