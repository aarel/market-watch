from datetime import date

from server.domain.compliance import ComplianceModel
from server.domain.corporate_actions import CorporateActionEvent, CorporateActionModel, CorporateActionType
from server.domain.cost_basis import CostBasisEngine
from server.domain.performance import PerformanceEngine
from server.domain.settlement import MarketProfile, SettlementEngine
from server.domain.tax import TaxModel


def test_buy_split_sell_lifecycle_realized_gain_and_settlement() -> None:
    settlement_engine = SettlementEngine(initial_settled_cash=10_000)
    compliance = ComplianceModel(settlement_engine=settlement_engine, enable_settlement_enforcement=True)
    corporate = CorporateActionModel()
    cost_basis = CostBasisEngine()
    tax_model = TaxModel(short_term_rate=0.30, long_term_rate=0.15)
    perf = PerformanceEngine(
        compliance_model=compliance,
        corporate_action_model=corporate,
        cost_basis_engine=cost_basis,
        tax_model=tax_model,
        settlement_engine=settlement_engine,
        enable_corporate_actions=True,
        enable_cost_basis_engine=True,
        enable_settlement_enforcement=True,
    )

    profile = MarketProfile(settlement_cycle="T+1", account_type="cash")

    buy = {
        "symbol": "ABC",
        "side": "buy",
        "qty": 10,
        "filled_avg_price": 100,
        "timestamp": "2026-01-05T10:00:00Z",
    }
    perf.process_trade(buy, market_profile=profile)

    split_event = CorporateActionEvent(
        event_id="evt-split",
        symbol="ABC",
        action_type=CorporateActionType.SPLIT,
        effective_date=date(2026, 1, 6),
        ratio=2.0,
    )

    sell = {
        "symbol": "ABC",
        "side": "sell",
        "qty": 10,
        "filled_avg_price": 60,
        "timestamp": "2026-01-07T10:00:00Z",
    }
    result = perf.process_trade(sell, market_profile=profile, corporate_events=[split_event])

    assert round(result.realized_gain, 8) == 100.0
    assert result.gross_pnl == result.realized_gain
    assert result.net_pnl < result.gross_pnl
    assert result.after_tax_pnl < result.net_pnl
    assert result.settlement_date == "2026-01-08"
    assert result.fee_breakdown["total_cost"] > 0
