"""Market calendar utilities: trading windows, FOMC blackout, earnings blackout."""
import json
import logging
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def is_in_trading_window(
    avoid_open_minutes: int,
    avoid_close_minutes: int,
    now: datetime | None = None,
) -> bool:
    """Return True if now is within the allowed intraday trading window.

    Avoids the first `avoid_open_minutes` minutes after 9:30 ET and the
    last `avoid_close_minutes` minutes before 16:00 ET. When both are 0
    (the default) the function always returns True so existing behaviour
    is unchanged.

    Args:
        avoid_open_minutes: Minutes to skip after market open (0 = disabled).
        avoid_close_minutes: Minutes to skip before market close (0 = disabled).
        now: Current time (defaults to datetime.now in ET). Injected for tests.
    """
    if avoid_open_minutes <= 0 and avoid_close_minutes <= 0:
        return True

    if now is None:
        now = datetime.now(_ET)
    else:
        now = now.astimezone(_ET)

    now_time = now.time().replace(tzinfo=None)

    if avoid_open_minutes > 0:
        window_start = (
            datetime.combine(now.date(), _MARKET_OPEN) + timedelta(minutes=avoid_open_minutes)
        ).time()
        if now_time < window_start:
            return False

    if avoid_close_minutes > 0:
        window_end = (
            datetime.combine(now.date(), _MARKET_CLOSE) - timedelta(minutes=avoid_close_minutes)
        ).time()
        if now_time >= window_end:
            return False

    return True


class FomcCalendar:
    """Checks whether today is an FOMC announcement day.

    Loads dates from ``data/shared/fomc_dates.json``. If the file is
    missing or unreadable the calendar is empty and ``is_fomc_day``
    always returns False (fail-open).
    """

    _DEFAULT_PATH = Path("data/shared/fomc_dates.json")

    def __init__(self, dates_path: Path | None = None):
        self._dates: set[date] = set()
        self._load(dates_path or self._DEFAULT_PATH)

    def is_fomc_day(self, today: date | None = None) -> bool:
        """Return True if today is an FOMC announcement day."""
        today = today or datetime.now(_ET).date()
        return today in self._dates

    @property
    def dates(self) -> frozenset:
        return frozenset(self._dates)

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self._dates = {date.fromisoformat(d) for d in data.get("dates", [])}
        except Exception as exc:
            logger.warning(f"FomcCalendar: could not load {path}: {exc}")


class EarningsCache:
    """Per-day cache of upcoming earnings dates fetched via yfinance.

    Results are cached per symbol for one calendar day. If yfinance is
    unavailable or returns no data the cache stores ``None`` and
    ``is_in_blackout`` returns False (fail-open — never blocks a trade
    due to missing data).
    """

    def __init__(self, blackout_days: int = 1):
        self.blackout_days = blackout_days
        self._cache: dict[str, date | None] = {}
        self._cache_date: date | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_in_blackout(self, symbol: str, today: date | None = None) -> bool:
        """Return True if *today* is within ``blackout_days`` of earnings.

        Fail-open: returns False when earnings data is unavailable.
        """
        if self.blackout_days <= 0:
            return False
        today = today or datetime.now(_ET).date()
        earnings = self.get_earnings_date(symbol, today)
        if earnings is None:
            return False
        return abs((earnings - today).days) <= self.blackout_days

    def get_earnings_date(self, symbol: str, today: date | None = None) -> date | None:
        """Return nearest upcoming earnings date for *symbol*, or None."""
        today = today or datetime.now(_ET).date()
        self._refresh_if_stale(today)
        if symbol not in self._cache:
            self._cache[symbol] = self._fetch(symbol)
        return self._cache[symbol]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_if_stale(self, today: date) -> None:
        if self._cache_date != today:
            self._cache.clear()
            self._cache_date = today

    def _fetch(self, symbol: str) -> date | None:
        """Fetch nearest earnings date from yfinance. Returns None on any error."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            if not cal or not isinstance(cal, dict):
                return None
            dates = cal.get("Earnings Date", [])
            if not dates:
                return None
            # dates is a list of Timestamps; take the earliest
            d = dates[0] if hasattr(dates, "__iter__") else dates
            if hasattr(d, "date"):
                return d.date()
            if hasattr(d, "to_pydatetime"):
                return d.to_pydatetime().date()
            return None
        except Exception as exc:
            logger.debug(f"EarningsCache: {symbol}: {exc}")
            return None
