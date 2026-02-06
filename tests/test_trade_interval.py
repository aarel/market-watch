import unittest

from agents.coordinator import Coordinator
from universe import Universe


class DummyBroker:
    pass


class TestTradeInterval(unittest.TestCase):
    def test_update_trade_interval(self):
        coordinator = Coordinator(DummyBroker(), universe=Universe.SIMULATION)
        coordinator.update_trade_interval(5)
        self.assertEqual(coordinator.data_agent.interval_minutes, 5)

    def test_update_trade_interval_requires_positive(self):
        coordinator = Coordinator(DummyBroker(), universe=Universe.SIMULATION)
        with self.assertRaises(ValueError):
            coordinator.update_trade_interval(0)


if __name__ == "__main__":
    unittest.main()
