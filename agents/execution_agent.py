"""Execution Agent - submits orders to the broker."""
import time
from typing import TYPE_CHECKING

from .base import BaseAgent
from .events import RiskCheckPassed, OrderExecuted, OrderFailed

if TYPE_CHECKING:
    from broker import AlpacaBroker
    from .event_bus import EventBus


class ExecutionAgent(BaseAgent):
    """Executes trades that pass risk validation."""

    def __init__(self, event_bus: "EventBus", broker: "AlpacaBroker", risk_agent=None):
        super().__init__("ExecutionAgent", event_bus)
        self.broker = broker
        self.risk_agent = risk_agent
        self._orders_executed = 0
        self._orders_failed = 0
        self._recent_orders = []

    async def start(self):
        """Start listening for approved trades."""
        await super().start()
        self.event_bus.subscribe(RiskCheckPassed, self._handle_approved_trade)

    async def stop(self):
        """Stop the agent."""
        self.event_bus.unsubscribe(RiskCheckPassed, self._handle_approved_trade)
        await super().stop()

    async def _handle_approved_trade(self, event: RiskCheckPassed):
        """Execute an approved trade."""
        import config

        if not config.AUTO_TRADE:
            return

        try:
            client_order_id = self._build_client_order_id("auto", event.symbol)
            if event.action == "buy":
                notional = self._round_notional(event.trade_value)
                order = self.broker.submit_order(
                    symbol=event.symbol,
                    notional=notional,
                    side="buy",
                    client_order_id=client_order_id,
                )
            elif event.action == "sell":
                position = self.broker.get_position(event.symbol)
                if position:
                    order = self.broker.submit_order(
                        symbol=event.symbol,
                        qty=position.qty,
                        side="sell",
                        client_order_id=client_order_id,
                    )
                else:
                    await self._fail(event, "Position not found")
                    return

            if order and getattr(order, "status", "filled") == "filled":
                await self._success(event, order)
                if self.risk_agent:
                    self.risk_agent.increment_trade_count()
            else:
                reason = getattr(order, "rejected_reason", None) or "Order returned None"
                await self._fail(event, reason)

        except Exception as e:
            await self._fail(event, str(e))

    async def execute_manual_trade(self, symbol: str, action: str, amount: float = None, qty: float = None, mode: str = "notional") -> dict:
        """Execute a manual trade (bypasses risk checks). Supports notional or share qty."""
        try:
            client_order_id = self._build_client_order_id("manual", symbol)
            if action == "buy":
                if mode == "qty":
                    if not qty or qty <= 0:
                        return {"success": False, "error": "Shares required for buy"}
                    order = self.broker.submit_order(
                        symbol=symbol,
                        qty=qty,
                        side="buy",
                        client_order_id=client_order_id,
                    )
                    notional = None
                else:
                    if not amount or amount <= 0:
                        return {"success": False, "error": "Amount required for buy"}
                    notional = self._round_notional(amount)
                    order = self.broker.submit_order(
                        symbol=symbol,
                        notional=notional,
                        side="buy",
                        client_order_id=client_order_id,
                    )
            elif action == "sell":
                position = self.broker.get_position(symbol)
                if not position:
                    return {"success": False, "error": f"No position in {symbol}"}
                sell_qty = None
                if mode == "qty":
                    sell_qty = qty if qty and qty > 0 else position.qty
                else:
                    # amount-based sell: convert to qty using latest price if available
                    if amount and amount > 0 and position.qty > 0:
                        price = float(getattr(position, "current_price", 0) or getattr(position, "avg_entry_price", 0) or 0)
                        if price > 0:
                            sell_qty = amount / price
                    if not sell_qty or sell_qty <= 0:
                        sell_qty = position.qty
                order = self.broker.submit_order(
                    symbol=symbol,
                    qty=sell_qty,
                    side="sell",
                    client_order_id=client_order_id,
                )
                notional = None
            else:
                return {"success": False, "error": "Action must be 'buy' or 'sell'"}

            if order:
                self._orders_executed += 1
                self._recent_orders.append({
                    "symbol": symbol,
                    "action": action,
                    "order_id": order.id,
                    "manual": True,
                })

                # Emit event
                event = OrderExecuted(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    symbol=symbol,
                    action=action,
                    notional=notional if action == "buy" else None,
                    qty=qty if mode == "qty" else getattr(order, "qty", None),
                    order_id=order.id,
                    **self._order_fields(order),
                )
                await self.event_bus.publish(event)

                return {"success": True, "order_id": order.id}
            else:
                return {"success": False, "error": "Order failed"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _success(self, event: RiskCheckPassed, order):
        """Record successful order execution."""
        self._orders_executed += 1
        self._recent_orders.append({
            "symbol": event.symbol,
            "action": event.action,
            "order_id": order.id,
            "trade_value": event.trade_value,
        })

        # Keep only last 50 orders
        if len(self._recent_orders) > 50:
            self._recent_orders = self._recent_orders[-50:]

        exec_event = OrderExecuted(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            symbol=event.symbol,
            action=event.action,
            notional=self._round_notional(event.trade_value) if event.action == "buy" else None,
            qty=getattr(order, "qty", None),
            order_id=order.id,
            **self._order_fields(order),
        )
        await self.event_bus.publish(exec_event)

    async def _fail(self, event: RiskCheckPassed, reason: str):
        """Record failed order execution."""
        self._orders_failed += 1
        fail_event = OrderFailed(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            symbol=event.symbol,
            action=event.action,
            reason=reason,
        )
        await self.event_bus.publish(fail_event)

    def _build_client_order_id(self, prefix: str, symbol: str) -> str:
        """Create a readable client order id for source tracking."""
        safe_symbol = symbol.replace(" ", "").replace("/", "_")
        return f"{prefix}-{safe_symbol}-{int(time.time() * 1000)}"

    def _order_fields(self, order) -> dict:
        """Extract common fields from an order object for analytics/logging."""
        def _float(value):
            try:
                return float(value)
            except Exception:
                return None

        # Explicitly avoid returning qty/notional here to prevent duplicate kwargs
        qty_val = _float(getattr(order, "qty", None))
        price_val = _float(getattr(order, "filled_avg_price", None))
        notional_val = _float(getattr(order, "notional", None))

        # Backfill price if possible (no duplication since we do not return notional/qty)
        if price_val is None and qty_val and notional_val:
            price_val = notional_val / qty_val if qty_val else None

        return {
            "filled_avg_price": price_val,
            "submitted_at": getattr(order, "submitted_at", None),
            "filled_at": getattr(order, "filled_at", None),
            "status": getattr(order, "status", "") or "filled",
            "time_in_force": getattr(order, "time_in_force", ""),
            "order_type": getattr(order, "type", "") or getattr(order, "order_type", ""),
        }

    @staticmethod
    def _round_notional(value: float) -> float:
        """Round dollar notional to two decimals to satisfy broker constraints."""
        if value is None:
            return 0.0
        return round(float(value), 2)

    def status(self) -> dict:
        """Get agent status."""
        base = super().status()
        base["orders_executed"] = self._orders_executed
        base["orders_failed"] = self._orders_failed
        base["recent_orders"] = len(self._recent_orders)
        return base
