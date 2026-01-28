"""Circuit breaker for automated trading halts."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo


@dataclass
class CircuitBreakerState:
    active: bool = False
    reason: str | None = None
    activated_at: str | None = None
    daily_start_equity: float | None = None
    peak_equity: float | None = None
    last_date: str | None = None


class CircuitBreaker:
    """Tracks portfolio drawdowns and halts trading when limits are breached."""

    def __init__(
        self,
        daily_loss_limit_pct: float,
        max_drawdown_pct: float,
        market_timezone: str,
    ):
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.market_timezone = market_timezone
        self.state = CircuitBreakerState()

    def update(self, equity: float, now: datetime | None = None) -> tuple[bool, str | None]:
        """Update breaker state and return (active, reason)."""
        if equity is None or equity <= 0:
            return self.state.active, self.state.reason

        timestamp = now or self._now()
        today = timestamp.date().isoformat()

        if self.state.last_date != today:
            self.state.last_date = today
            self.state.daily_start_equity = equity
            self.state.peak_equity = equity
            self.state.active = False
            self.state.reason = None
            self.state.activated_at = None

        if self.state.peak_equity is None or equity > self.state.peak_equity:
            self.state.peak_equity = equity

        daily_loss = _pct_change(equity, self.state.daily_start_equity)
        drawdown = _drawdown_pct(equity, self.state.peak_equity)

        if self.daily_loss_limit_pct and daily_loss <= -self.daily_loss_limit_pct:
            return self._activate(
                f"Daily loss limit hit ({daily_loss:.1%} <= -{self.daily_loss_limit_pct:.1%})",
                timestamp,
            )

        if self.max_drawdown_pct and drawdown >= self.max_drawdown_pct:
            return self._activate(
                f"Max drawdown limit hit ({drawdown:.1%} >= {self.max_drawdown_pct:.1%})",
                timestamp,
            )

        return self.state.active, self.state.reason

    def reset(self):
        """Manually reset breaker state."""
        self.state = CircuitBreakerState()

    def status(self) -> dict:
        """Return breaker status for UI or logging."""
        return {
            "active": self.state.active,
            "reason": self.state.reason,
            "activated_at": self.state.activated_at,
            "daily_start_equity": self.state.daily_start_equity,
            "peak_equity": self.state.peak_equity,
            "last_date": self.state.last_date,
        }

    def _activate(self, reason: str, timestamp: datetime) -> tuple[bool, str]:
        self.state.active = True
        self.state.reason = reason
        self.state.activated_at = timestamp.isoformat()
        return True, reason

    def _now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.market_timezone))
        except ZoneInfoNotFoundError:
            # Fallback for invalid timezone string
            return datetime.now()
        except Exception:
            # Fallback for other unexpected errors
            return datetime.now()


def _pct_change(value: float, base: float | None) -> float:
    if base is None or base == 0:
        return 0.0
    return (value - base) / base


def _drawdown_pct(value: float, peak: float | None) -> float:
    if peak is None or peak == 0:
        return 0.0
    return (peak - value) / peak
