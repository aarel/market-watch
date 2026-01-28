"""Lightweight file-based store for analytics data (equity curve and trades)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, date, timezone
from pathlib import Path
from threading import Lock
from typing import Iterable, List, Optional

from universe import Universe, get_log_path


class SchemaValidationError(ValueError):
    """Raised when a record fails schema validation."""
    pass


class AnalyticsStore:
    """
    Persist equity snapshots and trades to JSONL files for analytics.

    Universe-scoped: Each universe has its own isolated analytics data.
    """

    def __init__(self, universe: Universe):
        """
        Create analytics store for a specific universe.

        Args:
            universe: The execution universe (LIVE/PAPER/SIMULATION)
        """
        self.universe = universe

        # Universe-scoped paths
        base_dir = Path("logs") / universe.value
        base_dir.mkdir(parents=True, exist_ok=True)

        self.base_path = base_dir
        self.equity_path = Path(get_log_path(universe, "equity.jsonl"))
        self.trades_path = Path(get_log_path(universe, "trades.jsonl"))
        self._equity_lock = Lock()
        self._trades_lock = Lock()

    # --------------------
    # Write operations
    # --------------------
    def record_equity(self, snapshot: dict) -> None:
        """
        Append an equity snapshot to disk.

        Automatically tags with universe for provenance.
        Validates schema before writing.

        Args:
            snapshot: Equity snapshot dict. Should include session_id.

        Raises:
            SchemaValidationError: If snapshot fails validation
        """
        if not snapshot:
            return

        # Make a copy to avoid mutating input
        snapshot = dict(snapshot)

        # Default provenance fields if missing
        snapshot.setdefault("universe", self.universe.value)
        snapshot.setdefault("data_lineage_id", "unknown_lineage")
        snapshot.setdefault("validity_class", self.universe.default_validity_class)
        if "session_id" not in snapshot:
            raise SchemaValidationError("Equity snapshot missing 'session_id' field")

        # Validate universe if present (before we overwrite it)
        if "universe" in snapshot and snapshot["universe"] != self.universe.value:
            raise SchemaValidationError(
                f"Equity snapshot universe mismatch: "
                f"snapshot has '{snapshot['universe']}', "
                f"store expects '{self.universe.value}'"
            )

        # Add/overwrite universe tag for provenance
        snapshot["universe"] = self.universe.value

        # Default validity_class if missing
        if "validity_class" not in snapshot:
            snapshot["validity_class"] = self.universe.default_validity_class

        # Validate full schema
        self._validate_equity_schema(snapshot)

        with self._equity_lock:
            self._append_jsonl(self.equity_path, snapshot)

    def record_trade(self, trade: dict) -> None:
        """
        Append a trade record to disk.

        Automatically tags with universe and validity_class for provenance.
        Validates schema before writing.

        Args:
            trade: Trade record dict. Must include session_id, symbol, side.

        Raises:
            SchemaValidationError: If trade fails validation
        """
        if not trade:
            return

        # Make a copy to avoid mutating input
        trade = dict(trade)

        # Default provenance fields if missing
        trade.setdefault("universe", self.universe.value)
        trade.setdefault("data_lineage_id", "unknown_lineage")
        trade.setdefault("validity_class", self.universe.default_validity_class)
        if "session_id" not in trade:
            raise SchemaValidationError("Trade record missing 'session_id' field")

        # Validate universe if present (before we overwrite it)
        if "universe" in trade and trade["universe"] != self.universe.value:
            raise SchemaValidationError(
                f"Trade record universe mismatch: "
                f"trade has '{trade['universe']}', "
                f"store expects '{self.universe.value}'"
            )

        # Add/overwrite universe tag and validity class for provenance
        trade["universe"] = self.universe.value
        if "validity_class" not in trade:
            trade["validity_class"] = self.universe.default_validity_class

        # Validate full schema
        self._validate_trade_schema(trade)

        with self._trades_lock:
            self._append_jsonl(self.trades_path, trade)

    # --------------------
    # Read operations
    # --------------------
    def load_equity(self, period: str = "30d") -> list[dict]:
        """Load equity snapshots for the requested period."""
        cutoff = _cutoff_from_period(period)
        return list(_read_jsonl(self.equity_path, cutoff=cutoff))

    def load_trades(self, period: str = "90d", limit: int = 200) -> list[dict]:
        """Load recent trades for the requested period."""
        cutoff = _cutoff_from_period(period)
        trades = list(_read_jsonl(self.trades_path, cutoff=cutoff))
        if limit and limit > 0:
            return trades[-limit:]
        return trades

    # --------------------
    # Schema Validation
    # --------------------
    def _validate_equity_schema(self, snapshot: dict) -> None:
        """
        Validate equity snapshot has required fields.

        Required fields:
        - universe: Must match store's universe
        - session_id: Must be present and non-empty

        Args:
            snapshot: Equity snapshot to validate

        Raises:
            SchemaValidationError: If validation fails
        """
        # Validate universe
        if "universe" not in snapshot:
            raise SchemaValidationError("Equity snapshot missing 'universe' field")

        if snapshot["universe"] != self.universe.value:
            raise SchemaValidationError(
                f"Equity snapshot universe mismatch: "
                f"snapshot has '{snapshot['universe']}', "
                f"store expects '{self.universe.value}'"
            )

        # Validate session_id
        if "session_id" not in snapshot:
            raise SchemaValidationError("Equity snapshot missing 'session_id' field")

        if not snapshot["session_id"]:
            raise SchemaValidationError("Equity snapshot has empty 'session_id'")

        # Validate data_lineage_id
        if "data_lineage_id" not in snapshot:
            raise SchemaValidationError("Equity snapshot missing 'data_lineage_id' field")

        if not snapshot["data_lineage_id"]:
            raise SchemaValidationError("Equity snapshot has empty 'data_lineage_id'")

    def _validate_trade_schema(self, trade: dict) -> None:
        """
        Validate trade record has required fields.

        Required fields:
        - universe: Must match store's universe
        - session_id: Must be present and non-empty
        - symbol: Must be present
        - side: Must be 'buy' or 'sell'

        Args:
            trade: Trade record to validate

        Raises:
            SchemaValidationError: If validation fails
        """
        # Validate universe
        if "universe" not in trade:
            raise SchemaValidationError("Trade record missing 'universe' field")

        if trade["universe"] != self.universe.value:
            raise SchemaValidationError(
                f"Trade record universe mismatch: "
                f"trade has '{trade['universe']}', "
                f"store expects '{self.universe.value}'"
            )

        # Validate session_id
        if "session_id" not in trade:
            raise SchemaValidationError("Trade record missing 'session_id' field")

        if not trade["session_id"]:
            raise SchemaValidationError("Trade record has empty 'session_id'")

        # Validate required trading fields
        if "symbol" not in trade:
            raise SchemaValidationError("Trade record missing 'symbol' field")

        if "side" not in trade:
            raise SchemaValidationError("Trade record missing 'side' field")

        if trade["side"] not in ("buy", "sell"):
            raise SchemaValidationError(
                f"Trade record has invalid 'side': '{trade['side']}'. "
                f"Must be 'buy' or 'sell'"
            )

        # Validate data lineage
        if "data_lineage_id" not in trade:
            raise SchemaValidationError("Trade record missing 'data_lineage_id' field")
        if not trade["data_lineage_id"]:
            raise SchemaValidationError("Trade record has empty 'data_lineage_id'")

        # Validate validity_class
        if "validity_class" not in trade or not trade["validity_class"]:
            raise SchemaValidationError("Trade record missing 'validity_class' field")

    # --------------------
    # Helpers
    # --------------------
    @staticmethod
    def _append_jsonl(path: Path, obj: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        obj = dict(obj)
        if "timestamp" not in obj:
            obj["timestamp"] = datetime.now(timezone.utc).isoformat()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(obj, default=_json_default))
            handle.write("\n")


def _read_jsonl(path: Path, cutoff: Optional[datetime] = None) -> Iterable[dict]:
    if not path.exists():
        return []
    results: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(obj.get("timestamp"))
            if cutoff and ts and ts < cutoff:
                continue
            results.append(obj)
    return results


def _parse_ts(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _cutoff_from_period(period: str) -> Optional[datetime]:
    period = (period or "").lower()
    now = datetime.now(timezone.utc)
    if period in ("", "all"):
        return None
    if period == "ytd":
        start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        return start
    if period.endswith("d"):
        try:
            days = int(period[:-1])
            return now - timedelta(days=days)
        except Exception:
            return None
    if period.endswith("w"):
        try:
            weeks = int(period[:-1])
            return now - timedelta(weeks=weeks)
        except Exception:
            return None
    if period.endswith("m"):
        try:
            months = int(period[:-1])
            # approximate month as 30 days to avoid external deps
            return now - timedelta(days=months * 30)
        except Exception:
            return None
    return None


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return str(obj)
