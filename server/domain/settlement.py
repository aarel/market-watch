"""Settlement cycle accounting and cash-availability enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class MarketProfile:
    settlement_cycle: str = "T+1"
    account_type: str = "cash"


@dataclass
class SettlementEntry:
    settlement_date: date
    amount: float


class SettlementEngine:
    def __init__(self, initial_settled_cash: float = 0.0) -> None:
        self._settled_cash = float(initial_settled_cash)
        self._pending_credits: list[SettlementEntry] = []
        self._unsettled_cash = 0.0

    def register_trade(self, trade: dict[str, Any], market_profile: MarketProfile) -> date:
        trade_date = _parse_datetime(trade.get("timestamp") or trade.get("trade_date"))
        settlement_date = self.compute_settlement_date(trade_date, market_profile)
        side = str(trade.get("side", "")).lower()
        notional = _trade_notional(trade)

        if side == "buy":
            if market_profile.account_type.lower() == "cash":
                if not self.validate_cash_trade(trade, market_profile):
                    raise ValueError("Insufficient settled cash for buy trade")
                self._settled_cash -= notional
        elif side == "sell":
            self._pending_credits.append(SettlementEntry(settlement_date=settlement_date, amount=notional))

        self.update_unsettled_cash(as_of=trade_date.date())
        return settlement_date

    def compute_settlement_date(self, trade_date: datetime | date | str, market_profile: MarketProfile) -> date:
        if isinstance(trade_date, str):
            base_date = _parse_datetime(trade_date).date()
        elif isinstance(trade_date, datetime):
            base_date = trade_date.date()
        else:
            base_date = trade_date
        cycle = _settlement_days(market_profile.settlement_cycle)
        return _add_business_days(base_date, cycle)

    def update_unsettled_cash(self, as_of: date | None = None) -> None:
        today = as_of or datetime.now(UTC).date()
        matured: list[SettlementEntry] = []
        pending: list[SettlementEntry] = []
        for entry in self._pending_credits:
            if entry.settlement_date <= today:
                matured.append(entry)
            else:
                pending.append(entry)
        self._pending_credits = pending
        self._settled_cash += sum(item.amount for item in matured)
        self._unsettled_cash = sum(item.amount for item in self._pending_credits)

    def get_available_cash(self, as_of: date | None = None) -> float:
        self.update_unsettled_cash(as_of=as_of)
        return float(self._settled_cash)

    def validate_cash_trade(self, trade: dict[str, Any], market_profile: MarketProfile) -> bool:
        if market_profile.account_type.lower() == "margin":
            return True
        side = str(trade.get("side", "")).lower()
        if side != "buy":
            return True
        notional = _trade_notional(trade)
        return self.get_available_cash() >= notional


def _settlement_days(value: str) -> int:
    cleaned = value.strip().upper()
    if cleaned.startswith("T+"):
        return int(cleaned.split("+", 1)[1])
    if cleaned.startswith("T") and cleaned[1:].isdigit():
        return int(cleaned[1:])
    raise ValueError(f"Invalid settlement cycle: {value}")


def _add_business_days(start: date, days: int) -> date:
    cursor = start
    added = 0
    while added < days:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            added += 1
    return cursor


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=UTC)
    elif isinstance(value, str) and value:
        raw = value
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
    else:
        dt = datetime.now(UTC)

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _trade_notional(trade: dict[str, Any]) -> float:
    explicit = trade.get("notional")
    if explicit is not None:
        return float(explicit)
    qty = float(trade.get("qty") or 0.0)
    price = float(trade.get("filled_avg_price") or trade.get("price") or 0.0)
    return qty * price
