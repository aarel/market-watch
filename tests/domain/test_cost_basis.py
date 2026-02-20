from server.domain.corporate_actions import CorporateActionEvent, CorporateActionType
from server.domain.cost_basis import CostBasisEngine
import pytest


def _buy(symbol: str, qty: float, price: float, ts: str) -> dict:
    return {"symbol": symbol, "side": "buy", "qty": qty, "filled_avg_price": price, "timestamp": ts}


def _sell(symbol: str, qty: float, price: float, ts: str) -> dict:
    return {"symbol": symbol, "side": "sell", "qty": qty, "filled_avg_price": price, "timestamp": ts}


def test_fifo_lot_closing_realized_gain() -> None:
    engine = CostBasisEngine()
    engine.add_lot(_buy("ABC", 10, 100, "2026-01-01T10:00:00Z"))
    engine.add_lot(_buy("ABC", 10, 120, "2026-01-02T10:00:00Z"))
    result = engine.compute_realized_gain(_sell("ABC", 10, 130, "2026-01-10T10:00:00Z"), method="FIFO")
    assert result["realized_gain"] == 300.0
    assert result["holding_period_days"] == 9


def test_lifo_lot_closing_realized_gain() -> None:
    engine = CostBasisEngine()
    engine.add_lot(_buy("ABC", 10, 100, "2026-01-01T10:00:00Z"))
    engine.add_lot(_buy("ABC", 10, 120, "2026-01-02T10:00:00Z"))
    result = engine.compute_realized_gain(_sell("ABC", 10, 130, "2026-01-10T10:00:00Z"), method="LIFO")
    assert result["realized_gain"] == 100.0


def test_apply_split_updates_open_lots() -> None:
    engine = CostBasisEngine()
    engine.add_lot(_buy("ABC", 10, 100, "2026-01-01T10:00:00Z"))
    event = CorporateActionEvent(
        event_id="split-1",
        symbol="ABC",
        action_type=CorporateActionType.SPLIT,
        effective_date="2026-01-05",  # not used in test logic
        ratio=2.0,
    )
    engine.apply_corporate_action(event)
    lots = engine.get_open_lots("ABC")
    assert len(lots) == 1
    assert lots[0].remaining_quantity == 20.0
    assert lots[0].adjusted_cost_basis == 50.0


def test_add_lot_requires_explicit_timestamp() -> None:
    engine = CostBasisEngine()
    with pytest.raises(ValueError, match="Explicit datetime value is required"):
        engine.add_lot({"symbol": "ABC", "side": "buy", "qty": 1, "filled_avg_price": 100})


def test_close_lot_requires_explicit_timestamp() -> None:
    engine = CostBasisEngine()
    engine.add_lot(_buy("ABC", 1, 100, "2026-01-01T10:00:00Z"))
    with pytest.raises(ValueError, match="Explicit datetime value is required"):
        engine.compute_realized_gain({"symbol": "ABC", "side": "sell", "qty": 1, "filled_avg_price": 110})
