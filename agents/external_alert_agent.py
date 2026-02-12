"""External Alert Agent - routes critical events to alert channels."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from datetime import datetime
from typing import TYPE_CHECKING

from alerts.manager import get_manager
from alerts.models import AlertSeverity, AlertTrigger

from .base import BaseAgent
from .events import LogEvent, OrderFailed, RiskCheckFailed

if TYPE_CHECKING:
    from .event_bus import EventBus


class ExternalAlertAgent(BaseAgent):
    """Triggers external alerts for critical runtime events."""

    def __init__(self, event_bus: EventBus, cooldown_seconds: int = 600):
        super().__init__("ExternalAlertAgent", event_bus)
        self._cooldown_seconds = max(60, cooldown_seconds)
        self._last_alert_at: dict[tuple, datetime] = {}

    async def start(self):
        await super().start()
        self.event_bus.subscribe(RiskCheckFailed, self._handle_risk_failed)
        self.event_bus.subscribe(OrderFailed, self._handle_order_failed)
        self.event_bus.subscribe(LogEvent, self._handle_log_event)

    async def stop(self):
        self.event_bus.unsubscribe(RiskCheckFailed, self._handle_risk_failed)
        self.event_bus.unsubscribe(OrderFailed, self._handle_order_failed)
        self.event_bus.unsubscribe(LogEvent, self._handle_log_event)
        await super().stop()

    async def _handle_risk_failed(self, event: RiskCheckFailed):
        reason = event.reason or ""
        if "Circuit breaker active" not in reason:
            return

        trigger = AlertTrigger.CIRCUIT_BREAKER
        severity = AlertSeverity.HIGH
        if "Daily loss limit hit" in reason:
            trigger = AlertTrigger.DAILY_LOSS_LIMIT
            severity = AlertSeverity.CRITICAL
        elif "Max drawdown limit hit" in reason:
            trigger = AlertTrigger.MAX_DRAWDOWN
            severity = AlertSeverity.CRITICAL

        key = (trigger.value, reason)
        if not self._should_alert(key, event.timestamp):
            return

        title = "Circuit breaker activated"
        message = reason
        context = {
            "symbol": event.symbol,
            "action": event.action,
            "reason": reason,
        }
        await self._send_alert(trigger, severity, title, message, context)

    async def _handle_order_failed(self, event: OrderFailed):
        reason = event.reason or "Order failed"
        key = (AlertTrigger.ORDER_FAILED.value, event.symbol, reason)
        if not self._should_alert(key, event.timestamp):
            return

        title = f"Order failed: {event.symbol}"
        message = reason
        context = {
            "symbol": event.symbol,
            "action": event.action,
            "reason": reason,
        }
        await self._send_alert(AlertTrigger.ORDER_FAILED, AlertSeverity.HIGH, title, message, context)

    async def _handle_log_event(self, event: LogEvent):
        level = (event.level or "").lower()
        if level not in ("error", "critical"):
            return

        severity = AlertSeverity.CRITICAL if level == "critical" else AlertSeverity.HIGH
        key = (AlertTrigger.SYSTEM_ERROR.value, event.source, event.message)
        if not self._should_alert(key, event.timestamp):
            return

        title = f"System error: {event.source}"
        message = event.message or "System error reported"
        context = {
            "source": event.source,
            "level": event.level,
        }
        await self._send_alert(AlertTrigger.SYSTEM_ERROR, severity, title, message, context)

    def _should_alert(self, key: tuple, timestamp: datetime) -> bool:
        last = self._last_alert_at.get(key)
        if last:
            elapsed = (timestamp - last).total_seconds()
            if elapsed < self._cooldown_seconds:
                return False
        self._last_alert_at[key] = timestamp
        return True

    async def _send_alert(
        self,
        trigger: AlertTrigger,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: dict,
    ) -> None:
        try:
            manager = get_manager()
            await manager.trigger_alert(
                trigger_type=trigger,
                severity=severity,
                title=title,
                message=message,
                context=context,
            )
        except Exception as exc:
            logger.error(f"Error: {exc}")
