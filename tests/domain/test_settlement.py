from server.domain.settlement import MarketProfile, SettlementEngine


def _trade(side: str, qty: float, price: float, ts: str) -> dict:
    return {"side": side, "qty": qty, "filled_avg_price": price, "timestamp": ts}


def test_settlement_cycle_t1_and_t2() -> None:
    engine = SettlementEngine(initial_settled_cash=1000)
    friday = "2026-01-02T14:00:00Z"
    t1 = engine.compute_settlement_date(friday, MarketProfile(settlement_cycle="T+1", account_type="cash"))
    t2 = engine.compute_settlement_date(friday, MarketProfile(settlement_cycle="T+2", account_type="cash"))
    assert t1.isoformat() == "2026-01-05"
    assert t2.isoformat() == "2026-01-06"


def test_cash_restriction_enforced() -> None:
    engine = SettlementEngine(initial_settled_cash=100)
    profile = MarketProfile(settlement_cycle="T+1", account_type="cash")
    allowed = engine.validate_cash_trade(_trade("buy", 2, 60, "2026-01-05T10:00:00Z"), profile)
    assert allowed is False


def test_margin_account_bypasses_cash_check() -> None:
    engine = SettlementEngine(initial_settled_cash=0)
    profile = MarketProfile(settlement_cycle="T+2", account_type="margin")
    allowed = engine.validate_cash_trade(_trade("buy", 100, 100, "2026-01-05T10:00:00Z"), profile)
    assert allowed is True
