"""Lot-level cost basis accounting engine.

Contract:
- Input schema:
  - Trades are mappings containing `symbol`, `qty`, `filled_avg_price` or `price`,
    and explicit `timestamp` or `entry_date`/`exit_date`.
  - Corporate actions are `CorporateActionEvent`.
- Output schema:
  - `add_lot` returns a `Lot`.
  - `close_lot`/`compute_realized_gain` return realized-gain payload dictionaries.
- Determinism guarantee:
  - Deterministic for identical explicit inputs; no system-time fallbacks.
- No-mutation guarantee:
  - Caller trade mappings are never mutated.
  - Engine-managed lot state mutates only inside the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .corporate_actions import CorporateActionEvent, CorporateActionType


@dataclass
class Lot:
    lot_id: str
    symbol: str
    quantity: float
    entry_price: float
    entry_date: datetime
    remaining_quantity: float
    adjusted_cost_basis: float


@dataclass
class LotCloseResult:
    lot_id: str
    quantity_closed: float
    realized_gain: float
    holding_period_days: int


class CostBasisEngine:
    """Track open lots by symbol and compute realized gains on closure."""

    def __init__(self) -> None:
        self._lots: dict[str, list[Lot]] = {}
        self._sequence = 0

    def add_lot(self, trade: dict[str, Any]) -> Lot:
        symbol = str(trade.get("symbol", "")).upper()
        qty = float(trade.get("qty") or 0.0)
        price = float(trade.get("filled_avg_price") or trade.get("price") or 0.0)
        entry_date = _parse_datetime(trade.get("timestamp") or trade.get("entry_date"))
        if not symbol or qty <= 0 or price <= 0:
            raise ValueError("Invalid trade for lot creation")

        self._sequence += 1
        lot = Lot(
            lot_id=f"LOT-{self._sequence:06d}",
            symbol=symbol,
            quantity=qty,
            entry_price=price,
            entry_date=entry_date,
            remaining_quantity=qty,
            adjusted_cost_basis=price,
        )
        self._lots.setdefault(symbol, []).append(lot)
        return lot

    def close_lot(self, trade: dict[str, Any], method: str = "FIFO") -> dict[str, Any]:
        symbol = str(trade.get("symbol", "")).upper()
        qty_to_close = float(trade.get("qty") or 0.0)
        exit_price = float(trade.get("filled_avg_price") or trade.get("price") or 0.0)
        exit_date = _parse_datetime(trade.get("timestamp") or trade.get("exit_date"))
        if not symbol or qty_to_close <= 0 or exit_price <= 0:
            raise ValueError("Invalid trade for lot closure")

        open_lots = self._ordered_lots(symbol, method, trade)
        closed: list[LotCloseResult] = []
        remaining = qty_to_close

        for lot in open_lots:
            if remaining <= 0:
                break
            if lot.remaining_quantity <= 0:
                continue
            close_qty = min(remaining, lot.remaining_quantity)
            gain = (exit_price - float(lot.adjusted_cost_basis)) * close_qty
            holding_days = max((exit_date - lot.entry_date).days, 0)
            lot.remaining_quantity -= close_qty
            remaining -= close_qty
            closed.append(
                LotCloseResult(
                    lot_id=lot.lot_id,
                    quantity_closed=close_qty,
                    realized_gain=gain,
                    holding_period_days=holding_days,
                )
            )

        if remaining > 1e-9:
            raise ValueError("Insufficient lot inventory to close trade")

        realized_gain = sum(item.realized_gain for item in closed)
        weighted_holding_days = _weighted_holding_period(closed)
        return {
            "realized_gain": realized_gain,
            "holding_period_days": weighted_holding_days,
            "closed_lots": [item.__dict__ for item in closed],
        }

    def compute_realized_gain(self, exit_trade: dict[str, Any], method: str = "FIFO") -> dict[str, Any]:
        return self.close_lot(exit_trade, method=method)

    def apply_corporate_action(self, event: CorporateActionEvent) -> None:
        symbol = event.symbol
        lots = self._lots.get(symbol, [])
        if not lots:
            return

        if event.action_type == CorporateActionType.SPLIT:
            ratio = float(event.ratio or 0.0)
            if ratio <= 0:
                raise ValueError("Split ratio must be positive")
            for lot in lots:
                lot.quantity *= ratio
                lot.remaining_quantity *= ratio
                lot.adjusted_cost_basis /= ratio
        elif event.action_type == CorporateActionType.REVERSE_SPLIT:
            ratio = float(event.ratio or 0.0)
            if ratio <= 0:
                raise ValueError("Reverse split ratio must be positive")
            for lot in lots:
                lot.quantity /= ratio
                lot.remaining_quantity /= ratio
                lot.adjusted_cost_basis *= ratio
        elif event.action_type == CorporateActionType.SYMBOL_CHANGE:
            new_symbol = str(event.metadata.get("new_symbol", "")).upper()
            if not new_symbol:
                return
            moved = self._lots.pop(symbol, [])
            for lot in moved:
                lot.symbol = new_symbol
            self._lots.setdefault(new_symbol, []).extend(moved)

    def get_open_lots(self, symbol: str) -> list[Lot]:
        sym = symbol.upper()
        return [lot for lot in self._lots.get(sym, []) if lot.remaining_quantity > 0]

    def _ordered_lots(self, symbol: str, method: str, trade: dict[str, Any]) -> list[Lot]:
        lots = [lot for lot in self._lots.get(symbol, []) if lot.remaining_quantity > 0]
        normalized = method.upper()
        if normalized == "FIFO":
            return sorted(lots, key=lambda lot: lot.entry_date)
        if normalized == "LIFO":
            return sorted(lots, key=lambda lot: lot.entry_date, reverse=True)
        if normalized == "SPECIFIC_ID":
            ids = [str(item) for item in (trade.get("specific_lot_ids") or [])]
            if not ids:
                return lots
            rank = {lot_id: idx for idx, lot_id in enumerate(ids)}
            return sorted(lots, key=lambda lot: rank.get(lot.lot_id, len(ids)))
        raise ValueError(f"Unsupported lot method: {method}")


def _parse_datetime(value: Any) -> datetime:
    """Parse explicit timestamps deterministically; no implicit now() fallback."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        raw = value
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    else:
        raise ValueError("Explicit datetime value is required")

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _weighted_holding_period(closed: list[LotCloseResult]) -> int:
    total_qty = sum(item.quantity_closed for item in closed)
    if total_qty <= 0:
        return 0
    weighted = sum(item.holding_period_days * item.quantity_closed for item in closed) / total_qty
    return int(round(weighted))
