"""Componentized deterministic trade cost model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class FeeSchedule:
    commission_rate: float = 0.0
    spread_rate: float = 0.0
    slippage_rate: float = 0.0
    regulatory_fee_rate: float = 0.0
    borrow_fee_rate: float = 0.0
    margin_interest_rate_daily: float = 0.0
    fx_spread_rate: float = 0.0
    pre_after_hours_multiplier: float = 1.0


@dataclass(frozen=True)
class CostBreakdown:
    commission: float
    spread: float
    slippage: float
    regulatory_fees: float
    borrow_fee: float
    margin_interest: float
    fx_spread: float
    session_multiplier: float
    total_cost: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


class CostModel:
    def __init__(self, schedule: FeeSchedule | None = None) -> None:
        self.schedule = schedule or FeeSchedule()

    def total(
        self,
        trade: dict[str, Any],
        account: dict[str, Any] | None = None,
        market: dict[str, Any] | None = None,
        session: dict[str, Any] | None = None,
        execution_details: dict[str, Any] | None = None,
    ) -> CostBreakdown:
        del market, execution_details

        notional = _trade_notional(trade)
        is_short = bool(trade.get("is_short") or False)
        holding_days = float(trade.get("holding_period_days") or 1.0)
        fx_applied = bool(trade.get("fx_applied") or False)

        session_multiplier = 1.0
        if session and str(session.get("type", "")).upper() in {"PRE", "POST", "AFTER_HOURS", "PRE_MARKET"}:
            session_multiplier = float(self.schedule.pre_after_hours_multiplier)

        commission = notional * float(self.schedule.commission_rate)
        spread = notional * float(self.schedule.spread_rate) * session_multiplier
        slippage = notional * float(self.schedule.slippage_rate) * session_multiplier
        regulatory_fees = notional * float(self.schedule.regulatory_fee_rate)
        borrow_fee = notional * float(self.schedule.borrow_fee_rate) if is_short else 0.0

        margin_enabled = bool((account or {}).get("margin_enabled") or False)
        margin_interest = (
            notional * float(self.schedule.margin_interest_rate_daily) * max(holding_days, 0.0)
            if margin_enabled else 0.0
        )

        fx_spread = notional * float(self.schedule.fx_spread_rate) if fx_applied else 0.0

        total_cost = commission + spread + slippage + regulatory_fees + borrow_fee + margin_interest + fx_spread
        return CostBreakdown(
            commission=commission,
            spread=spread,
            slippage=slippage,
            regulatory_fees=regulatory_fees,
            borrow_fee=borrow_fee,
            margin_interest=margin_interest,
            fx_spread=fx_spread,
            session_multiplier=session_multiplier,
            total_cost=total_cost,
        )


def _trade_notional(trade: dict[str, Any]) -> float:
    explicit = trade.get("notional")
    if explicit is not None:
        return float(explicit)
    qty = float(trade.get("qty") or 0.0)
    price = float(trade.get("filled_avg_price") or trade.get("price") or 0.0)
    return qty * price
