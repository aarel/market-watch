from datetime import UTC, datetime, timedelta, timezone

import pytest

from analytics.metrics import compute_period_returns

pytestmark = [pytest.mark.stress, pytest.mark.whitebox]


def test_period_returns_light_stress():
    base = datetime(2025, 1, 1, tzinfo=UTC)
    equity_points = []
    equity = 100000.0
    for i in range(5000):
        ts = base + timedelta(minutes=i)
        equity += 1.0
        equity_points.append({"timestamp": ts.isoformat(), "equity": equity})

    returns = compute_period_returns(equity_points, granularity="daily")
    # Expect multiple daily buckets; ensure we got a reasonable number of returns
    assert len(returns) >= 2
    # Sanity check: return pct should be positive
    assert all(r["return_pct"] >= 0 for r in returns)
