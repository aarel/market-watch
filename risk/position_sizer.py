"""Position sizing logic for risk management."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PositionSizer:
    """Compute position sizes based on risk settings and signal strength."""

    scale_by_strength: bool = True
    min_strength: float = 0.0
    max_strength: float = 1.0

    def calculate_trade_value(
        self,
        signal_strength: float,
        account_value: float,
        buying_power: float,
        max_position_pct: float,
    ) -> float:
        """Return a dollar trade value based on risk constraints.

        Args:
            signal_strength: Strategy signal strength (0.0 to 1.0 expected).
            account_value: Total portfolio value.
            buying_power: Available buying power.
            max_position_pct: Maximum position size as fraction of portfolio.
        """
        base_value = min(account_value * max_position_pct, buying_power)
        if base_value <= 0:
            return 0.0

        strength = _clamp(signal_strength, self.min_strength, self.max_strength)
        if self.scale_by_strength:
            base_value *= strength

        return max(base_value, 0.0)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    if value is None:
        value = 0.0
    value = max(value, min_value)
    return min(value, max_value)
