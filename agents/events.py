"""Event definitions for agent communication."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from universe import Universe


@dataclass
class Event:
    """
    Base event class with universe provenance.

    All events MUST be constructed with universe and session_id.
    These fields are not optional - illegal states are unrepresentable.

    Agents receive universe and session_id from Coordinator at initialization
    and must pass them to all events they create.
    """
    # Required provenance fields (no defaults)
    universe: Universe
    session_id: str
    data_lineage_id: Optional[str] = None
    validity_class: Optional[str] = None

    # Standard fields with defaults
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""


@dataclass
class MarketDataReady(Event):
    """Emitted when market data has been fetched."""
    symbols: list[str] = field(default_factory=list)
    prices: dict[str, float] = field(default_factory=dict)
    bars: dict[str, Any] = field(default_factory=dict)
    account: dict[str, float] = field(default_factory=dict)
    positions: list[dict[str, float]] = field(default_factory=list)
    top_gainers: list[dict[str, Any]] = field(default_factory=list)
    market_indices: list[dict[str, Any]] = field(default_factory=list)
    market_open: bool = False


@dataclass
class SignalGenerated(Event):
    """Emitted when a trading signal is generated."""
    symbol: str = ""
    action: str = ""  # "buy", "sell", "hold"
    strength: float = 0.0
    reason: str = ""
    current_price: float = 0.0
    momentum: float = 0.0


@dataclass
class SignalsUpdated(Event):
    """Emitted when all signals have been refreshed."""
    signals: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RiskCheckPassed(Event):
    """Emitted when a trade passes risk validation."""
    symbol: str = ""
    action: str = ""
    trade_value: float = 0.0
    position_pct: float = 0.0
    reason: str = ""


@dataclass
class RiskCheckFailed(Event):
    """Emitted when a trade fails risk validation."""
    symbol: str = ""
    action: str = ""
    reason: str = ""


@dataclass
class OrderExecuted(Event):
    """Emitted when an order is successfully executed."""
    symbol: str = ""
    action: str = ""
    qty: Optional[float] = None
    notional: Optional[float] = None
    order_id: str = ""
    filled_avg_price: Optional[float] = None
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    status: str = ""
    time_in_force: str = ""
    order_type: str = ""


@dataclass
class OrderFailed(Event):
    """Emitted when an order fails."""
    symbol: str = ""
    action: str = ""
    reason: str = ""


@dataclass
class StopLossTriggered(Event):
    """Emitted when a position hits stop loss."""
    symbol: str = ""
    entry_price: float = 0.0
    current_price: float = 0.0
    loss_pct: float = 0.0
    position_value: float = 0.0


@dataclass
class LogEvent(Event):
    """Emitted to broadcast a generic log message."""
    level: str = "info"  # "info", "warning", "error"
    message: str = ""
