from datetime import date

from server.domain.corporate_actions import CorporateActionEvent, CorporateActionModel, CorporateActionType
from server.domain.cost_basis import Lot


def test_split_adjusts_position_and_lot_basis() -> None:
    model = CorporateActionModel()
    event = CorporateActionEvent(
        event_id="evt-split",
        symbol="ABC",
        action_type=CorporateActionType.SPLIT,
        effective_date=date(2026, 1, 10),
        ratio=2.0,
    )

    position = {"symbol": "ABC", "quantity": 10.0, "entry_price": 100.0}
    model.apply_to_position(position, event)
    assert position["quantity"] == 20.0
    assert position["entry_price"] == 50.0

    lot = Lot(
        lot_id="LOT-1",
        symbol="ABC",
        quantity=10.0,
        entry_price=100.0,
        entry_date=date(2026, 1, 1),
        remaining_quantity=10.0,
        adjusted_cost_basis=100.0,
    )
    model.apply_to_lots([lot], event)
    assert lot.quantity == 20.0
    assert lot.remaining_quantity == 20.0
    assert lot.adjusted_cost_basis == 50.0


def test_reverse_split_preserves_total_basis() -> None:
    model = CorporateActionModel()
    event = CorporateActionEvent(
        event_id="evt-rsplit",
        symbol="ABC",
        action_type=CorporateActionType.REVERSE_SPLIT,
        effective_date=date(2026, 1, 10),
        ratio=5.0,
    )
    position = {"symbol": "ABC", "quantity": 100.0, "entry_price": 2.0}
    before_total = position["quantity"] * position["entry_price"]
    model.apply_to_position(position, event)
    after_total = position["quantity"] * position["entry_price"]
    assert round(before_total, 8) == round(after_total, 8)


def test_dividend_records_cash_inflow() -> None:
    model = CorporateActionModel()
    event = CorporateActionEvent(
        event_id="evt-div",
        symbol="ABC",
        action_type=CorporateActionType.DIVIDEND,
        effective_date=date(2026, 1, 10),
        cash_amount=0.25,
    )
    position = {"symbol": "ABC", "quantity": 40.0}
    model.apply_to_position(position, event)
    assert position["cash_dividend"] == 10.0
