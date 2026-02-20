from server.domain.settlement import MarketProfile, SettlementEngine
import pytest


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


def test_validate_cash_trade_requires_explicit_trade_time_for_cash() -> None:
    engine = SettlementEngine(initial_settled_cash=1000)
    profile = MarketProfile(settlement_cycle="T+1", account_type="cash")
    with pytest.raises(ValueError, match="Explicit datetime value is required"):
        engine.validate_cash_trade({"side": "buy", "qty": 1, "filled_avg_price": 10}, profile)


def test_get_available_cash_requires_explicit_as_of() -> None:
    engine = SettlementEngine(initial_settled_cash=1000)
    with pytest.raises(ValueError, match="Explicit as_of date is required"):
        engine.get_available_cash()
