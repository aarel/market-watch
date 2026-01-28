"""Alert Agent - handles notifications and WebSocket broadcasts."""
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Optional

from .base import BaseAgent
from .events import (
    Event,
    LogEvent,
    MarketDataReady,
    SignalGenerated,
    RiskCheckPassed,
    RiskCheckFailed,
    OrderExecuted,
    OrderFailed,
    StopLossTriggered,
)

if TYPE_CHECKING:
    from .event_bus import EventBus


class AlertAgent(BaseAgent):
    """Listens to all events and broadcasts to UI/webhooks."""

    def __init__(self, event_bus: "EventBus"):
        super().__init__("AlertAgent", event_bus)
        self._log: list[dict] = []
        self._max_log_size = 100
        self._broadcast_callback: Optional[Callable] = None

    async def start(self):
        """Start listening to all events."""
        await super().start()
        self.event_bus.subscribe_all(self._handle_event)

    async def stop(self):
        """Stop listening."""
        self.event_bus.unsubscribe_all(self._handle_event)
        await super().stop()

    def set_broadcast_callback(self, callback: Callable):
        """Set the callback for broadcasting to WebSocket clients."""
        self._broadcast_callback = callback

    async def _handle_event(self, event: Event):
        """Process and log any event."""
        log_entry = self._event_to_log(event)
        if log_entry:
            self._log.append(log_entry)
            if len(self._log) > self._max_log_size:
                self._log = self._log[-self._max_log_size:]

            # Broadcast to WebSocket clients
            if self._broadcast_callback:
                try:
                    await self._broadcast_callback({"event": "log", "entry": log_entry})
                except Exception as e:
                    print(f"AlertAgent broadcast error: {e}")

    def _event_to_log(self, event: Event) -> Optional[dict]:
        """Convert an event to a log entry."""
        timestamp = event.timestamp.isoformat()

        if isinstance(event, MarketDataReady):
            return {
                "timestamp": timestamp,
                "type": "info",
                "message": f"Market data fetched for {len(event.symbols)} symbols",
                "data": {"symbols": event.symbols, "market_open": event.market_open},
            }

        elif isinstance(event, SignalGenerated):
            if event.action == "hold":
                return None  # Don't log hold signals
            return {
                "timestamp": timestamp,
                "type": "signal",
                "message": f"{event.action.upper()} signal: {event.symbol} - {event.reason}",
                "data": {
                    "symbol": event.symbol,
                    "action": event.action,
                    "price": event.current_price,
                    "momentum": event.momentum,
                },
            }

        elif isinstance(event, RiskCheckPassed):
            return {
                "timestamp": timestamp,
                "type": "info",
                "message": f"Risk approved: {event.action.upper()} {event.symbol} ${event.trade_value:.2f}",
                "data": {
                    "symbol": event.symbol,
                    "action": event.action,
                    "trade_value": event.trade_value,
                },
            }

        elif isinstance(event, RiskCheckFailed):
            return {
                "timestamp": timestamp,
                "type": "warning",
                "message": f"Risk rejected: {event.symbol} - {event.reason}",
                "data": {"symbol": event.symbol, "action": event.action, "reason": event.reason},
            }

        elif isinstance(event, OrderExecuted):
            return {
                "timestamp": timestamp,
                "type": "trade",
                "message": f"Order executed: {event.action.upper()} {event.symbol}",
                "data": {
                    "symbol": event.symbol,
                    "action": event.action,
                    "order_id": event.order_id,
                },
            }

        elif isinstance(event, OrderFailed):
            return {
                "timestamp": timestamp,
                "type": "error",
                "message": f"Order failed: {event.symbol} - {event.reason}",
                "data": {"symbol": event.symbol, "action": event.action, "reason": event.reason},
            }

        elif isinstance(event, StopLossTriggered):
            return {
                "timestamp": timestamp,
                "type": "warning",
                "message": f"STOP LOSS: {event.symbol} down {event.loss_pct:.1%}",
                "data": {
                    "symbol": event.symbol,
                    "entry_price": event.entry_price,
                    "current_price": event.current_price,
                    "loss_pct": event.loss_pct,
                },
            }

        elif isinstance(event, LogEvent):
            return {
                "timestamp": timestamp,
                "type": event.level,
                "message": event.message,
                "data": {"source": event.source},
            }

        return None

    def get_logs(self, count: int = 50) -> list[dict]:
        """Get recent log entries."""
        return self._log[-count:]

    def status(self) -> dict:
        """Get agent status."""
        base = super().status()
        base["log_entries"] = len(self._log)
        return base
