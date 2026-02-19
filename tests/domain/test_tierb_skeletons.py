from server.domain.fx_timing import FxTimingMode, FxTimingModel
from server.domain.margin import MarginModel, MarginProfile


def test_margin_model_placeholder_deterministic_behavior() -> None:
    model = MarginModel(MarginProfile(initial_margin_rate=0.5, daily_interest_rate=0.001))
    required = model.compute_required_margin(1000.0)
    interest = model.compute_margin_interest(balance=1000.0, days=2)
    assert required == 500.0
    assert interest == 2.0


def test_fx_timing_modes_trade_vs_settlement_date() -> None:
    trade_model = FxTimingModel(mode=FxTimingMode.TRADE_DATE)
    settle_model = FxTimingModel(mode=FxTimingMode.SETTLEMENT_DATE)

    trade_result = trade_model.convert(amount_quote=100, trade_date_rate=1.2, settlement_date_rate=1.3)
    settle_result = settle_model.convert(amount_quote=100, trade_date_rate=1.2, settlement_date_rate=1.3)

    assert trade_result.amount_base == 120.0
    assert settle_result.amount_base == 130.0
