"""Tier B FX timing skeleton (gated deterministic placeholder)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FxTimingMode(str, Enum):
    TRADE_DATE = "TRADE_DATE"
    SETTLEMENT_DATE = "SETTLEMENT_DATE"


@dataclass(frozen=True)
class FxConversionResult:
    amount_base: float
    fx_rate: float
    mode: FxTimingMode


class FxTimingModel:
    def __init__(self, mode: FxTimingMode = FxTimingMode.TRADE_DATE) -> None:
        self.mode = mode

    def convert(self, amount_quote: float, trade_date_rate: float, settlement_date_rate: float | None = None) -> FxConversionResult:
        quote = float(amount_quote)
        trade_rate = float(trade_date_rate)
        settle_rate = float(settlement_date_rate if settlement_date_rate is not None else trade_rate)

        fx_rate = trade_rate if self.mode == FxTimingMode.TRADE_DATE else settle_rate
        return FxConversionResult(amount_base=quote * fx_rate, fx_rate=fx_rate, mode=self.mode)
