"""Observability Agent - structured logging and context annotation."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import BaseAgent
from .events import (
    Event,
    MarketDataReady,
    SignalsUpdated,
    SignalGenerated,
    RiskCheckPassed,
    RiskCheckFailed,
    OrderExecuted,
    OrderFailed,
    StopLossTriggered,
)
from monitoring.context import MarketContextTracker
from monitoring.logger import JSONLLogger, SystemLogWriter
from universe import Universe
from monitoring.models import Observation
from monitoring.reason_codes import classify_event
from monitoring.anomaly_detector import get_detector
from alerts.manager import get_manager
from alerts.models import AlertTrigger, AlertSeverity

if TYPE_CHECKING:
    from .event_bus import EventBus


class ObservabilityAgent(BaseAgent):
    """Captures structured logs for all events and annotates context."""

    def __init__(self, event_bus: "EventBus", log_path: str, max_log_mb: float = 5.0):
        super().__init__("ObservabilityAgent", event_bus)
        # Prefer universe-scoped system log writer when possible
        if log_path.startswith("logs/"):
            self._logger = SystemLogWriter(self.universe, filename=log_path.split("/")[-1], max_mb=max_log_mb)
        else:
            self._logger = JSONLLogger(log_path, max_log_mb)
        self._context_tracker = MarketContextTracker()
        self._baseline_initialized = False
        self._last_anomaly_alert_at: datetime | None = None
        self._anomaly_alert_cooldown_seconds = 600

    async def start(self):
        """Start listening to all events."""
        await super().start()
        self.event_bus.subscribe_all(self._handle_event)

    async def stop(self):
        """Stop listening to all events."""
        self.event_bus.unsubscribe_all(self._handle_event)
        await super().stop()

    async def _handle_event(self, event: Event):
        try:
            reason_code, outcome = classify_event(event)
            context = self._build_context(event)
            inputs, outputs = self._build_io(event)

            observation = Observation(
                timestamp=event.timestamp,
                event_type=type(event).__name__,
                agent=event.source or "unknown",
                action=getattr(event, "action", None),
                symbol=getattr(event, "symbol", None),
                outcome=outcome,
                reason=getattr(event, "reason", None),
                reason_code=reason_code,
                latency_ms=getattr(event, "latency_ms", None),
                inputs=inputs,
                outputs=outputs,
                context=context,
            )
            self._logger.write(observation.to_dict())

            # Record event for anomaly detection
            if outcome in ("warn", "fail"):
                detector = get_detector()
                detector.record_event(outcome, event.timestamp)
                self._maybe_initialize_baseline(detector)
                await self._maybe_alert_on_anomaly(detector, event.timestamp)

        except Exception as exc:
            print(f"ObservabilityAgent error: {exc}")

    def _build_context(self, event: Event) -> dict[str, Any]:
        if isinstance(event, MarketDataReady):
            context = self._context_tracker.update(event)
        else:
            context = self._context_tracker.get()
        return context.to_dict()

    def _build_io(self, event: Event) -> tuple[dict[str, Any], dict[str, Any]]:
        inputs: dict[str, Any] = {}
        outputs: dict[str, Any] = {}

        if isinstance(event, MarketDataReady):
            symbol_count = len(event.symbols)
            price_count = len(event.prices or {})
            bars_count = len(event.bars or {})

            inputs["symbol_count"] = symbol_count
            inputs["market_open"] = event.market_open
            outputs["price_count"] = price_count
            outputs["bars_count"] = bars_count
            outputs["top_gainers_count"] = len(event.top_gainers or [])
            outputs["missing_price_ratio"] = _safe_ratio(symbol_count - price_count, symbol_count)
            outputs["bars_coverage_ratio"] = _safe_ratio(bars_count, symbol_count)

        elif isinstance(event, SignalsUpdated):
            total = len(event.signals or [])
            actionable = sum(1 for s in event.signals if s.get("action") != "hold")
            holds = total - actionable
            errors = sum(1 for s in event.signals if "error" in (s.get("reason", "").lower()))

            outputs["signal_count"] = total
            outputs["actionable_count"] = actionable
            outputs["hold_count"] = holds
            outputs["signal_error_count"] = errors
            outputs["actionable_ratio"] = _safe_ratio(actionable, total)
            outputs["signal_error_ratio"] = _safe_ratio(errors, total)

        elif isinstance(event, SignalGenerated):
            inputs["current_price"] = event.current_price
            inputs["strength"] = event.strength
            outputs["momentum"] = event.momentum

        elif isinstance(event, RiskCheckPassed):
            inputs["trade_value"] = event.trade_value
            inputs["position_pct"] = event.position_pct
            outputs["approved"] = True

        elif isinstance(event, RiskCheckFailed):
            inputs["action"] = event.action
            outputs["approved"] = False

        elif isinstance(event, OrderExecuted):
            inputs["notional"] = event.notional
            inputs["qty"] = event.qty
            outputs["order_id"] = event.order_id

        elif isinstance(event, OrderFailed):
            inputs["action"] = event.action
            outputs["order_failed"] = True

        elif isinstance(event, StopLossTriggered):
            inputs["entry_price"] = event.entry_price
            inputs["current_price"] = event.current_price
            outputs["loss_pct"] = event.loss_pct
            outputs["position_value"] = event.position_value

        return inputs, outputs

    def _maybe_initialize_baseline(self, detector) -> None:
        if self._baseline_initialized:
            return
        detector.update_baseline()
        status = detector.get_status()
        if status["warn_events"]["baseline_rate"] is not None or status["fail_events"]["baseline_rate"] is not None:
            self._baseline_initialized = True

    async def _maybe_alert_on_anomaly(self, detector, timestamp: datetime) -> None:
        anomaly = detector.detect_anomaly()
        if not anomaly:
            return

        now = datetime.now()
        if self._last_anomaly_alert_at:
            elapsed = (now - self._last_anomaly_alert_at).total_seconds()
            if elapsed < self._anomaly_alert_cooldown_seconds:
                return

        severity = AlertSeverity.HIGH if anomaly.get("severity") == "high" else AlertSeverity.MEDIUM
        title = "Observability anomaly detected"
        message = anomaly.get("message", "Anomaly detected in warn/fail event rates.")
        context = {
            "type": anomaly.get("type"),
            "current_rate": anomaly.get("current_rate"),
            "baseline_rate": anomaly.get("baseline_rate"),
            "multiplier": anomaly.get("multiplier"),
            "event_count": anomaly.get("event_count"),
        }

        try:
            manager = get_manager()
            await manager.trigger_alert(
                trigger_type=AlertTrigger.ANOMALY_DETECTED,
                severity=severity,
                title=title,
                message=message,
                context=context,
            )
            self._last_anomaly_alert_at = now
        except Exception as exc:
            print(f"ObservabilityAgent anomaly alert error: {exc}")


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator
