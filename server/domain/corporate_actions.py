"""Corporate action processing for position and lot adjustments."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class CorporateActionType(str, Enum):
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    DIVIDEND = "DIVIDEND"
    MERGER = "MERGER"
    SPINOFF = "SPINOFF"
    SYMBOL_CHANGE = "SYMBOL_CHANGE"


@dataclass(frozen=True)
class CorporateActionEvent:
    event_id: str
    symbol: str
    action_type: CorporateActionType
    effective_date: date
    ratio: float | None = None
    cash_amount: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CorporateActionModel:
    """Stores and applies deterministic corporate action adjustments."""

    def __init__(self) -> None:
        self._events: list[CorporateActionEvent] = []

    def register_event(self, event: CorporateActionEvent) -> None:
        self._events.append(event)

    def apply_to_position(self, position: dict[str, Any], event: CorporateActionEvent) -> dict[str, Any]:
        if position.get("symbol") != event.symbol:
            return position

        if event.action_type == CorporateActionType.SPLIT:
            ratio = _require_ratio(event)
            qty = float(position.get("quantity", 0.0))
            entry_price = float(position.get("entry_price", 0.0))
            position["quantity"] = qty * ratio
            position["entry_price"] = entry_price / ratio if ratio else entry_price
        elif event.action_type == CorporateActionType.REVERSE_SPLIT:
            ratio = _require_ratio(event)
            qty = float(position.get("quantity", 0.0))
            entry_price = float(position.get("entry_price", 0.0))
            position["quantity"] = qty / ratio if ratio else qty
            position["entry_price"] = entry_price * ratio
        elif event.action_type == CorporateActionType.DIVIDEND:
            qty = float(position.get("quantity", 0.0))
            cash = float(event.cash_amount or 0.0)
            position["cash_dividend"] = float(position.get("cash_dividend", 0.0)) + (qty * cash)
        elif event.action_type == CorporateActionType.SYMBOL_CHANGE:
            self.handle_symbol_change(position, event)
        elif event.action_type in {CorporateActionType.MERGER, CorporateActionType.SPINOFF}:
            # Placeholder: no valuation math, allow target symbol override.
            target = event.metadata.get("target_symbol")
            if target:
                position["symbol"] = str(target)
        return position

    def apply_to_lots(self, lots: list[Any], event: CorporateActionEvent) -> list[Any]:
        adjusted: list[Any] = []
        for lot in lots:
            symbol = getattr(lot, "symbol", None)
            if symbol != event.symbol:
                adjusted.append(lot)
                continue

            if event.action_type == CorporateActionType.SPLIT:
                ratio = _require_ratio(event)
                lot.quantity = float(lot.quantity) * ratio
                lot.remaining_quantity = float(lot.remaining_quantity) * ratio
                lot.adjusted_cost_basis = float(lot.adjusted_cost_basis) / ratio if ratio else float(lot.adjusted_cost_basis)
            elif event.action_type == CorporateActionType.REVERSE_SPLIT:
                ratio = _require_ratio(event)
                lot.quantity = float(lot.quantity) / ratio if ratio else float(lot.quantity)
                lot.remaining_quantity = float(lot.remaining_quantity) / ratio if ratio else float(lot.remaining_quantity)
                lot.adjusted_cost_basis = float(lot.adjusted_cost_basis) * ratio
            elif event.action_type == CorporateActionType.SYMBOL_CHANGE:
                lot.symbol = str(event.metadata.get("new_symbol", lot.symbol))
            elif event.action_type in {CorporateActionType.MERGER, CorporateActionType.SPINOFF}:
                target = event.metadata.get("target_symbol")
                if target:
                    lot.symbol = str(target)
            adjusted.append(lot)
        return adjusted

    def adjust_cost_basis(self, lots: list[Any], event: CorporateActionEvent) -> list[Any]:
        return self.apply_to_lots(lots, event)

    def handle_symbol_change(self, position: dict[str, Any], event: CorporateActionEvent) -> dict[str, Any]:
        new_symbol = event.metadata.get("new_symbol")
        if new_symbol:
            position["symbol"] = str(new_symbol)
        return position


def _require_ratio(event: CorporateActionEvent) -> float:
    ratio = float(event.ratio or 0.0)
    if ratio <= 0:
        raise ValueError(f"Corporate action {event.event_id} requires positive ratio")
    return ratio
