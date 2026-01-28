"""Reason code mapping for structured observability logs."""
from __future__ import annotations

from typing import Tuple

from agents.events import (
    Event,
    MarketDataReady,
    SignalGenerated,
    SignalsUpdated,
    RiskCheckPassed,
    RiskCheckFailed,
    OrderExecuted,
    OrderFailed,
    StopLossTriggered,
)


def classify_event(event: Event) -> Tuple[str, str]:
    """Return (reason_code, outcome) for a given event."""
    if isinstance(event, MarketDataReady):
        return "market_data_ready", "info"

    if isinstance(event, SignalsUpdated):
        return "signals_updated", "info"

    if isinstance(event, SignalGenerated):
        reason = (event.reason or "").lower()
        if event.action == "hold":
            if "insufficient" in reason:
                return "signal_insufficient_history", "info"
            if "error" in reason:
                return "signal_error", "warn"
            return "signal_hold", "info"
        if "error" in reason:
            return "signal_error", "warn"
        return f"signal_{event.action}", "success"

    if isinstance(event, RiskCheckPassed):
        return "risk_passed", "success"

    if isinstance(event, RiskCheckFailed):
        reason = (event.reason or "").lower()
        if "daily trade limit" in reason:
            return "risk_daily_limit", "warn"
        if "trade value" in reason and "minimum" in reason:
            return "risk_min_trade", "warn"
        if "insufficient buying power" in reason:
            return "risk_buying_power", "warn"
        if "position lookup failed" in reason:
            return "risk_position_lookup_failed", "fail"
        if "no position" in reason:
            return "risk_no_position", "warn"
        return "risk_rejected", "warn"

    if isinstance(event, OrderExecuted):
        return "order_executed", "success"

    if isinstance(event, OrderFailed):
        reason = (event.reason or "").lower()
        if "position not found" in reason:
            return "order_no_position", "warn"
        if "returned none" in reason:
            return "order_no_response", "fail"
        return "order_failed", "fail"

    if isinstance(event, StopLossTriggered):
        return "stop_loss_triggered", "warn"

    return "unknown_event", "info"
