import unittest

from agents.coordinator import Coordinator


class DummyBroker:
    pass


class TestTradeInterval(unittest.TestCase):
    def test_update_trade_interval(self):
        coordinator = Coordinator(DummyBroker())
        coordinator.update_trade_interval(5)
        self.assertEqual(coordinator.data_agent.interval_minutes, 5)

    def test_update_trade_interval_requires_positive(self):
        coordinator = Coordinator(DummyBroker())
        with self.assertRaises(ValueError):
            coordinator.update_trade_interval(0)


if __name__ == "__main__":
    unittest.main()
