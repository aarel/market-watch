"""Performance orchestration integrating compliance, cost basis, tax, and settlement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import config

from .compliance import ComplianceModel
from .cost_model import CostModel, FeeSchedule
from .corporate_actions import CorporateActionEvent, CorporateActionModel
from .cost_basis import CostBasisEngine
from .fx_timing import FxTimingModel, FxTimingMode
from .margin import MarginModel
from .settlement import MarketProfile, SettlementEngine
from .tax import TaxModel, TaxProfile


@dataclass
class PerformanceBreakdown:
    gross_pnl: float
    net_pnl: float
    after_tax_pnl: float
    realized_gain: float
    tax_estimate: float
    settlement_date: str | None
    fee_breakdown: dict[str, float]


class PerformanceEngine:
    def __init__(
        self,
        compliance_model: ComplianceModel,
        corporate_action_model: CorporateActionModel,
        cost_basis_engine: CostBasisEngine,
        tax_model: TaxModel,
        settlement_engine: SettlementEngine,
        cost_model: CostModel | None = None,
        margin_model: MarginModel | None = None,
        fx_timing_model: FxTimingModel | None = None,
        enable_corporate_actions: bool | None = None,
        enable_cost_basis_engine: bool | None = None,
        enable_settlement_enforcement: bool | None = None,
        enable_margin_model: bool | None = None,
        enable_fx_timing: bool | None = None,
    ) -> None:
        self.compliance_model = compliance_model
        self.corporate_action_model = corporate_action_model
        self.cost_basis_engine = cost_basis_engine
        self.tax_model = tax_model
        self.settlement_engine = settlement_engine
        self.cost_model = cost_model or CostModel(
            FeeSchedule(
                commission_rate=config.COST_COMMISSION_RATE,
                spread_rate=config.COST_SPREAD_RATE,
                slippage_rate=config.COST_SLIPPAGE_RATE,
                regulatory_fee_rate=config.COST_REGULATORY_FEE_RATE,
                borrow_fee_rate=config.COST_BORROW_FEE_RATE,
                margin_interest_rate_daily=config.COST_MARGIN_INTEREST_DAILY_RATE,
                fx_spread_rate=config.COST_FX_SPREAD_RATE,
                pre_after_hours_multiplier=config.COST_SESSION_MULTIPLIER_PRE_AFTER_HOURS,
            )
        )
        self.margin_model = margin_model or MarginModel()
        fx_mode = FxTimingMode(str(config.FX_TIMING_MODE).upper())
        self.fx_timing_model = fx_timing_model or FxTimingModel(mode=fx_mode)
        self.enable_corporate_actions = (
            config.ENABLE_CORPORATE_ACTIONS if enable_corporate_actions is None else enable_corporate_actions
        )
        self.enable_cost_basis_engine = (
            config.ENABLE_COST_BASIS_ENGINE if enable_cost_basis_engine is None else enable_cost_basis_engine
        )
        self.enable_settlement_enforcement = (
            config.ENABLE_SETTLEMENT_ENFORCEMENT
            if enable_settlement_enforcement is None
            else enable_settlement_enforcement
        )
        self.enable_margin_model = config.ENABLE_MARGIN_MODEL if enable_margin_model is None else enable_margin_model
        self.enable_fx_timing = config.ENABLE_FX_TIMING if enable_fx_timing is None else enable_fx_timing

    def process_trade(
        self,
        trade: dict[str, Any],
        market_profile: MarketProfile,
        corporate_events: list[CorporateActionEvent] | None = None,
        lot_method: str = "FIFO",
    ) -> PerformanceBreakdown:
        # 1) Compliance validation
        self.compliance_model.enable_settlement_enforcement = self.enable_settlement_enforcement
        ok, reason = self.compliance_model.validate_trade(trade, market_profile)
        if not ok:
            raise ValueError(f"Trade blocked by compliance: {reason}")

        # 2) Broker execution (input trade assumed executed)
        executed_trade = dict(trade)

        # 3) Corporate action adjustments
        if self.enable_corporate_actions and corporate_events:
            for event in corporate_events:
                self.corporate_action_model.register_event(event)
                self.cost_basis_engine.apply_corporate_action(event)

        side = str(executed_trade.get("side", "")).lower()

        # 4) Cost basis update and realized gain computation
        realized_gain = 0.0
        holding_days = 0
        if self.enable_cost_basis_engine:
            if side == "buy":
                self.cost_basis_engine.add_lot(executed_trade)
            elif side == "sell":
                result = self.cost_basis_engine.compute_realized_gain(executed_trade, method=lot_method)
                realized_gain = float(result["realized_gain"])
                holding_days = int(result["holding_period_days"])

        # 5) Preserve gross_pnl compatibility: explicit trade value has priority
        gross_pnl = float(executed_trade.get("gross_pnl") or realized_gain)

        # 6) Cost model application
        profile = TaxProfile(
            jurisdiction=config.TAX_JURISDICTION,
            short_term_rate=config.TAX_SHORT_TERM_RATE,
            long_term_rate=config.TAX_LONG_TERM_RATE,
            state_rate=config.TAX_STATE_RATE,
            disclaimer_required=config.TAX_DISCLAIMER_REQUIRED,
            foreign_withholding_rate=config.TAX_FOREIGN_WITHHOLDING_RATE,
            foreign_tax_credit_rate=config.TAX_FOREIGN_TAX_CREDIT_RATE,
        )
        if profile.jurisdiction.upper() not in self.tax_model.profiles:
            self.tax_model.profiles[profile.jurisdiction.upper()] = profile

        account = {"margin_enabled": bool(market_profile.account_type.lower() == "margin")}
        session = {"type": str(executed_trade.get("session_type", "REGULAR")).upper()}
        executed_trade["holding_period_days"] = holding_days

        if self.enable_margin_model and account["margin_enabled"]:
            margin_interest = self.margin_model.compute_margin_interest(
                balance=_trade_notional(executed_trade),
                days=max(holding_days, 1),
            )
            executed_trade["margin_interest_override"] = margin_interest

        if self.enable_fx_timing and executed_trade.get("fx_applied"):
            fx = self.fx_timing_model.convert(
                amount_quote=_trade_notional(executed_trade),
                trade_date_rate=float(executed_trade.get("trade_date_fx_rate") or 1.0),
                settlement_date_rate=float(executed_trade.get("settlement_date_fx_rate") or 1.0),
            )
            executed_trade["fx_rate_used"] = fx.fx_rate

        fee = self.cost_model.total(executed_trade, account=account, session=session)
        if "margin_interest_override" in executed_trade:
            d = fee.to_dict()
            d["margin_interest"] = float(executed_trade["margin_interest_override"])
            d["total_cost"] = (
                d["commission"]
                + d["spread"]
                + d["slippage"]
                + d["regulatory_fees"]
                + d["borrow_fee"]
                + d["margin_interest"]
                + d["fx_spread"]
            )
            fee_breakdown = d
        else:
            fee_breakdown = fee.to_dict()
        net_pnl = gross_pnl - fee_breakdown["total_cost"]

        # 7) Tax estimate (consumes realized gain)
        tax_estimate = self.tax_model.estimate_tax(
            realized_gain=realized_gain,
            holding_period_days=holding_days,
            jurisdiction=config.TAX_JURISDICTION,
        )
        after_tax_pnl = net_pnl - tax_estimate

        # 8) Settlement registration
        settlement_date = self.settlement_engine.register_trade(executed_trade, market_profile)

        # 9) Return aggregate summary
        return PerformanceBreakdown(
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            after_tax_pnl=after_tax_pnl,
            realized_gain=realized_gain,
            tax_estimate=tax_estimate,
            settlement_date=settlement_date.isoformat(),
            fee_breakdown=fee_breakdown,
        )


def _trade_notional(trade: dict[str, Any]) -> float:
    explicit = trade.get("notional")
    if explicit is not None:
        return float(explicit)
    qty = float(trade.get("qty") or 0.0)
    price = float(trade.get("filled_avg_price") or trade.get("price") or 0.0)
    return qty * price
