import unittest
from datetime import datetime, timedelta

from risk.circuit_breaker import CircuitBreaker


class TestCircuitBreaker(unittest.TestCase):
    def test_daily_loss_triggers(self):
        cb = CircuitBreaker(daily_loss_limit_pct=0.03, max_drawdown_pct=0.15, market_timezone="UTC")
        now = datetime(2025, 1, 1, 9, 30)

        cb.update(100000, now)
        active, reason = cb.update(96000, now + timedelta(minutes=5))

        self.assertTrue(active)
        self.assertIn("Daily loss limit", reason)

    def test_drawdown_triggers(self):
        cb = CircuitBreaker(daily_loss_limit_pct=0.0, max_drawdown_pct=0.1, market_timezone="UTC")
        now = datetime(2025, 1, 1, 9, 30)

        cb.update(100000, now)
        cb.update(110000, now + timedelta(minutes=1))
        active, reason = cb.update(98000, now + timedelta(minutes=2))

        self.assertTrue(active)
        self.assertIn("Max drawdown", reason)

    def test_resets_on_new_day(self):
        cb = CircuitBreaker(daily_loss_limit_pct=0.03, max_drawdown_pct=0.15, market_timezone="UTC")
        day1 = datetime(2025, 1, 1, 9, 30)
        day2 = datetime(2025, 1, 2, 9, 30)

        cb.update(100000, day1)
        cb.update(96000, day1 + timedelta(hours=1))
        self.assertTrue(cb.state.active)

        active, _ = cb.update(100000, day2)
        self.assertFalse(active)


if __name__ == "__main__":
    unittest.main()
