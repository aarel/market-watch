"""Tax estimation model consuming realized gain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TaxProfile:
    jurisdiction: str = "US"
    short_term_rate: float = 0.30
    long_term_rate: float = 0.15
    state_rate: float = 0.0
    disclaimer_required: bool = True
    foreign_withholding_rate: float = 0.0
    foreign_tax_credit_rate: float = 0.0


class TaxModel:
    def __init__(
        self,
        short_term_rate: float = 0.30,
        long_term_rate: float = 0.15,
        profiles: dict[str, TaxProfile] | None = None,
    ) -> None:
        default = TaxProfile(short_term_rate=short_term_rate, long_term_rate=long_term_rate)
        self.profiles = profiles or {"US": default}

    def estimate_tax(
        self,
        realized_gain: float,
        holding_period_days: int | None = None,
        jurisdiction: str = "US",
    ) -> float:
        if realized_gain <= 0:
            return 0.0
        profile = self.get_profile(jurisdiction)
        base_rate = profile.long_term_rate if holding_period_days is not None and holding_period_days >= 365 else profile.short_term_rate
        total_rate = base_rate + profile.state_rate
        gross_tax = realized_gain * total_rate
        withholding = realized_gain * profile.foreign_withholding_rate
        credit = realized_gain * profile.foreign_tax_credit_rate
        return max(gross_tax + withholding - credit, 0.0)

    def get_profile(self, jurisdiction: str) -> TaxProfile:
        key = str(jurisdiction or "US").upper()
        return self.profiles.get(key, self.profiles.get("US", TaxProfile()))

    def calculate(
        self,
        realized_lot_events: list[dict[str, Any]],
        jurisdiction: str | None = None,
        tax_profile: dict[str, Any] | None = None,
        lot_strategy: str | None = None,
    ) -> dict[str, Any]:
        profile = self.get_profile((jurisdiction or (tax_profile or {}).get("jurisdiction") or "US"))
        del lot_strategy
        total_gain = sum(float(item.get("realized_gain") or 0.0) for item in realized_lot_events)
        avg_holding_days = 0
        if realized_lot_events:
            avg_holding_days = int(
                round(sum(float(item.get("holding_period_days") or 0.0) for item in realized_lot_events) / len(realized_lot_events))
            )
        tax_estimate = self.estimate_tax(total_gain, avg_holding_days, jurisdiction=profile.jurisdiction)
        return {
            "jurisdiction": profile.jurisdiction,
            "realized_gain": total_gain,
            "tax_estimate": tax_estimate,
            "after_tax_pnl": total_gain - tax_estimate,
            "estimated_only": True,
            "disclaimer_required": profile.disclaimer_required,
            "foreign_withholding_rate": profile.foreign_withholding_rate,
            "foreign_tax_credit_rate": profile.foreign_tax_credit_rate,
        }
