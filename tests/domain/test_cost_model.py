from server.domain.cost_model import CostModel, FeeSchedule


def test_component_sum_equals_total_cost() -> None:
    model = CostModel(
        FeeSchedule(
            commission_rate=0.001,
            spread_rate=0.001,
            slippage_rate=0.001,
            regulatory_fee_rate=0.0001,
            borrow_fee_rate=0.0002,
            margin_interest_rate_daily=0.0001,
            fx_spread_rate=0.0003,
            pre_after_hours_multiplier=1.5,
        )
    )
    trade = {
        "qty": 10,
        "filled_avg_price": 100,
        "holding_period_days": 2,
        "is_short": True,
        "fx_applied": True,
    }
    breakdown = model.total(
        trade,
        account={"margin_enabled": True},
        session={"type": "PRE"},
    ).to_dict()

    summed = (
        breakdown["commission"]
        + breakdown["spread"]
        + breakdown["slippage"]
        + breakdown["regulatory_fees"]
        + breakdown["borrow_fee"]
        + breakdown["margin_interest"]
        + breakdown["fx_spread"]
    )
    assert round(summed, 10) == round(breakdown["total_cost"], 10)


def test_session_multiplier_changes_slippage_and_spread() -> None:
    model = CostModel(FeeSchedule(spread_rate=0.001, slippage_rate=0.001, pre_after_hours_multiplier=2.0))
    trade = {"qty": 5, "filled_avg_price": 100}
    regular = model.total(trade, session={"type": "REGULAR"}).to_dict()
    after_hours = model.total(trade, session={"type": "AFTER_HOURS"}).to_dict()

    assert after_hours["spread"] > regular["spread"]
    assert after_hours["slippage"] > regular["slippage"]


def test_borrow_fee_applies_only_when_short() -> None:
    model = CostModel(FeeSchedule(borrow_fee_rate=0.01))
    base_trade = {"qty": 1, "filled_avg_price": 100}
    long_cost = model.total(base_trade | {"is_short": False}).to_dict()
    short_cost = model.total(base_trade | {"is_short": True}).to_dict()

    assert long_cost["borrow_fee"] == 0.0
    assert short_cost["borrow_fee"] > 0.0
