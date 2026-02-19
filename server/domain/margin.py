"""Tier B margin model skeleton (gated placeholder)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarginProfile:
    initial_margin_rate: float = 0.50
    maintenance_margin_rate: float = 0.30
    daily_interest_rate: float = 0.0001


class MarginModel:
    def __init__(self, profile: MarginProfile | None = None) -> None:
        self.profile = profile or MarginProfile()

    def compute_required_margin(self, position_notional: float) -> float:
        value = max(float(position_notional), 0.0)
        return value * float(self.profile.initial_margin_rate)

    def compute_margin_interest(self, balance: float, days: int) -> float:
        bal = max(float(balance), 0.0)
        d = max(int(days), 0)
        return bal * float(self.profile.daily_interest_rate) * d
