"""Analytics Agent - captures equity snapshots and executed trades."""
from __future__ import annotations

from typing import TYPE_CHECKING

import config
from analytics.store import AnalyticsStore
from server.domain import (
    ComplianceModel,
    CorporateActionModel,
    CostBasisEngine,
    MarketProfile,
    PerformanceEngine,
    SettlementEngine,
    TaxModel,
)

from .base import BaseAgent
from .events import MarketDataReady, OrderExecuted

if TYPE_CHECKING:
    from broker import AlpacaBroker

    from .event_bus import EventBus


class AnalyticsAgent(BaseAgent):
    """Listens to events and persists analytics-friendly data."""

    def __init__(self, event_bus: EventBus, broker: AlpacaBroker, store: AnalyticsStore):
        super().__init__("AnalyticsAgent", event_bus)
        self.broker = broker
        self.store = store
        self._latest_cash: float = 0.0
        self._realism_initialized = False
        self._settlement_engine = SettlementEngine(initial_settled_cash=0.0)
        self._performance_engine = PerformanceEngine(
            compliance_model=ComplianceModel(self._settlement_engine, enable_settlement_enforcement=config.ENABLE_SETTLEMENT_ENFORCEMENT),
            corporate_action_model=CorporateActionModel(),
            cost_basis_engine=CostBasisEngine(),
            tax_model=TaxModel(),
            settlement_engine=self._settlement_engine,
            enable_corporate_actions=config.ENABLE_CORPORATE_ACTIONS,
            enable_cost_basis_engine=config.ENABLE_COST_BASIS_ENGINE,
            enable_settlement_enforcement=config.ENABLE_SETTLEMENT_ENFORCEMENT,
            enable_margin_model=config.ENABLE_MARGIN_MODEL,
            enable_fx_timing=config.ENABLE_FX_TIMING,
        )

    async def start(self):
        await super().start()
        self.event_bus.subscribe(MarketDataReady, self._handle_market_data)
        self.event_bus.subscribe(OrderExecuted, self._handle_order_executed)

    async def stop(self):
        self.event_bus.unsubscribe(MarketDataReady, self._handle_market_data)
        self.event_bus.unsubscribe(OrderExecuted, self._handle_order_executed)
        await super().stop()

    @staticmethod
    def _assert_no_unauthorized_pnl_inputs(trade: dict) -> None:
        unauthorized_keys = {
            "gross_pnl",
            "net_pnl",
            "after_tax_pnl",
            "realized_gain",
            "tax_estimate",
        }
        if any(k in trade for k in unauthorized_keys):
            raise RuntimeError("Unauthorized PnL computation path")

    async def _handle_market_data(self, event: MarketDataReady):
        account = event.account or {}
        if not account:
            return
        snapshot = {
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "equity": account.get("equity"),
            "portfolio_value": account.get("portfolio_value"),
            "cash": account.get("cash"),
            "buying_power": account.get("buying_power"),
            "market_open": event.market_open,
        }
        try:
            self._latest_cash = float(account.get("cash") or 0.0)
        except Exception:
            self._latest_cash = 0.0
        self.store.record_equity(snapshot)

    async def _handle_order_executed(self, event: OrderExecuted):
        # Only record orders that are actually filled
        # Pending/new/accepted orders don't have filled_avg_price yet
        status = (event.status or "").lower()
        if status not in ("filled", "partially_filled"):
            return  # Skip unfilled orders

        # Validate filled_avg_price is present
        if event.filled_avg_price is None or event.filled_avg_price <= 0:
            return  # Skip orders without valid fill price

        trade = {
            "session_id": event.session_id,
            "timestamp": event.timestamp,
            "order_id": event.order_id,
            "symbol": event.symbol,
            "side": event.action,
            "qty": event.qty,
            "filled_avg_price": event.filled_avg_price,
            "notional": event.notional,
            "status": event.status or "filled",
            "submitted_at": event.submitted_at,
            "filled_at": event.filled_at,
            "source": event.source,
            "time_in_force": event.time_in_force,
            "order_type": event.order_type,
        }
        # Backfill notional if missing and qty/price available
        if trade.get("notional") is None and trade.get("qty") and trade.get("filled_avg_price"):
            trade["notional"] = float(trade["qty"]) * float(trade["filled_avg_price"])

        if config.ENABLE_REALISM_PIPELINE:
            # Seed settlement cash from runtime account snapshot once.
            if not self._realism_initialized:
                self._settlement_engine = SettlementEngine(initial_settled_cash=self._latest_cash)
                self._performance_engine.settlement_engine = self._settlement_engine
                self._performance_engine.compliance_model.settlement_engine = self._settlement_engine
                self._realism_initialized = True

            profile = MarketProfile(
                settlement_cycle=config.DEFAULT_SETTLEMENT_CYCLE,
                account_type=config.REALISM_ACCOUNT_TYPE,
            )
            try:
                if config.REALISM_FAIL_FAST_PNL_GUARD:
                    self._assert_no_unauthorized_pnl_inputs(trade)
                breakdown = self._performance_engine.process_trade(trade, market_profile=profile)
                trade["gross_pnl"] = breakdown.gross_pnl
                trade["net_pnl"] = breakdown.net_pnl
                trade["after_tax_pnl"] = breakdown.after_tax_pnl
                trade["realized_gain"] = breakdown.realized_gain
                trade["tax_estimate"] = breakdown.tax_estimate
                trade["settlement_date"] = breakdown.settlement_date
                trade["fee_breakdown"] = breakdown.fee_breakdown
                trade["fees_total"] = breakdown.fee_breakdown.get("total_cost", 0.0)
                trade["margin_interest"] = breakdown.fee_breakdown.get("margin_interest", 0.0)
                trade["fx_rate_used"] = trade.get("fx_rate_used")
                trade["realism_pipeline_enabled"] = True
            except Exception as exc:
                trade["realism_pipeline_enabled"] = False
                trade["realism_processing_error"] = str(exc)
                if config.REALISM_FAIL_FAST_PNL_GUARD and str(exc) == "Unauthorized PnL computation path":
                    raise
        else:
            trade["realism_pipeline_enabled"] = False

        self.store.record_trade(trade)
