"""Compliance checks with settlement-aware cash validation."""

from __future__ import annotations

from typing import Any

from .settlement import MarketProfile, SettlementEngine


class ComplianceModel:
    def __init__(self, settlement_engine: SettlementEngine, enable_settlement_enforcement: bool = True) -> None:
        self.settlement_engine = settlement_engine
        self.enable_settlement_enforcement = enable_settlement_enforcement

    def validate_trade(self, trade: dict[str, Any], market_profile: MarketProfile) -> tuple[bool, str]:
        if not self.enable_settlement_enforcement:
            return True, "settlement enforcement disabled"
        allowed = self.settlement_engine.validate_cash_trade(trade, market_profile)
        if allowed:
            return True, "ok"
        return False, "insufficient settled cash"
