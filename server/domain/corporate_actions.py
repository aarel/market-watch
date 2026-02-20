"""Corporate action processing for position and lot adjustments.

Contract:
- Input schema:
  - Position: mapping with at least `symbol`; may include `quantity`, `entry_price`.
  - Lots: sequence of objects with `symbol`, `quantity`, `remaining_quantity`,
    and `adjusted_cost_basis` attributes.
  - Event: `CorporateActionEvent`.
- Output schema:
  - New position mapping and/or new lot-object list reflecting action adjustments.
- Determinism guarantee:
  - For the same input position/lots/event, output values are identical.
- No-mutation guarantee:
  - Caller-provided position mappings and lot objects are never mutated in place.
"""

from __future__ import annotations

from copy import deepcopy
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
    """Apply deterministic corporate action adjustments without mutating caller data."""

    def __init__(self) -> None:
        self._events: list[CorporateActionEvent] = []

    def register_event(self, event: CorporateActionEvent) -> None:
        self._events.append(event)

    def apply_to_position(self, position: dict[str, Any], event: CorporateActionEvent) -> dict[str, Any]:
        """Return a new adjusted position mapping for a corporate action event."""
        updated = dict(position)
        if updated.get("symbol") != event.symbol:
            return updated

        if event.action_type == CorporateActionType.SPLIT:
            ratio = _require_ratio(event)
            qty = float(updated.get("quantity", 0.0))
            entry_price = float(updated.get("entry_price", 0.0))
            updated["quantity"] = qty * ratio
            updated["entry_price"] = entry_price / ratio if ratio else entry_price
        elif event.action_type == CorporateActionType.REVERSE_SPLIT:
            ratio = _require_ratio(event)
            qty = float(updated.get("quantity", 0.0))
            entry_price = float(updated.get("entry_price", 0.0))
            updated["quantity"] = qty / ratio if ratio else qty
            updated["entry_price"] = entry_price * ratio
        elif event.action_type == CorporateActionType.DIVIDEND:
            qty = float(updated.get("quantity", 0.0))
            cash = float(event.cash_amount or 0.0)
            updated["cash_dividend"] = float(updated.get("cash_dividend", 0.0)) + (qty * cash)
        elif event.action_type == CorporateActionType.SYMBOL_CHANGE:
            updated = self.handle_symbol_change(updated, event)
        elif event.action_type in {CorporateActionType.MERGER, CorporateActionType.SPINOFF}:
            # Placeholder: no valuation math, allow target symbol override.
            target = event.metadata.get("target_symbol")
            if target:
                updated["symbol"] = str(target)
        return updated

    def apply_to_lots(self, lots: list[Any], event: CorporateActionEvent) -> list[Any]:
        """Return a new lot list with adjusted values; never mutates provided lot objects."""
        adjusted: list[Any] = []
        for lot in lots:
            clone = deepcopy(lot)
            symbol = getattr(clone, "symbol", None)
            if symbol != event.symbol:
                adjusted.append(clone)
                continue

            if event.action_type == CorporateActionType.SPLIT:
                ratio = _require_ratio(event)
                clone.quantity = float(clone.quantity) * ratio
                clone.remaining_quantity = float(clone.remaining_quantity) * ratio
                clone.adjusted_cost_basis = float(clone.adjusted_cost_basis) / ratio if ratio else float(clone.adjusted_cost_basis)
            elif event.action_type == CorporateActionType.REVERSE_SPLIT:
                ratio = _require_ratio(event)
                clone.quantity = float(clone.quantity) / ratio if ratio else float(clone.quantity)
                clone.remaining_quantity = float(clone.remaining_quantity) / ratio if ratio else float(clone.remaining_quantity)
                clone.adjusted_cost_basis = float(clone.adjusted_cost_basis) * ratio
            elif event.action_type == CorporateActionType.SYMBOL_CHANGE:
                clone.symbol = str(event.metadata.get("new_symbol", clone.symbol))
            elif event.action_type in {CorporateActionType.MERGER, CorporateActionType.SPINOFF}:
                target = event.metadata.get("target_symbol")
                if target:
                    clone.symbol = str(target)
            adjusted.append(clone)
        return adjusted

    def adjust_cost_basis(self, lots: list[Any], event: CorporateActionEvent) -> list[Any]:
        return self.apply_to_lots(lots, event)

    def handle_symbol_change(self, position: dict[str, Any], event: CorporateActionEvent) -> dict[str, Any]:
        """Return a new position mapping with updated symbol when provided."""
        updated = dict(position)
        new_symbol = event.metadata.get("new_symbol")
        if new_symbol:
            updated["symbol"] = str(new_symbol)
        return updated


def _require_ratio(event: CorporateActionEvent) -> float:
    ratio = float(event.ratio or 0.0)
    if ratio <= 0:
        raise ValueError(f"Corporate action {event.event_id} requires positive ratio")
    return ratio
