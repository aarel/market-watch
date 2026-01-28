import types
import unittest

from agents.execution_agent import ExecutionAgent
from universe import Universe, UniverseContext


class DummyEventBus:
    def __init__(self):
        self._context = UniverseContext(Universe.SIMULATION)

    def subscribe(self, *args, **kwargs):
        pass

    def unsubscribe(self, *args, **kwargs):
        pass

    async def publish(self, *args, **kwargs):
        pass


class TestExecutionAgentOrderFields(unittest.IsolatedAsyncioTestCase):
    async def test_backfills_price_only(self):
        agent = ExecutionAgent(DummyEventBus(), broker=None)
        order = types.SimpleNamespace(qty=2, filled_avg_price=5.5, notional=None, status="filled")
        fields = agent._order_fields(order)
        self.assertEqual(fields["filled_avg_price"], 5.5)
        self.assertEqual(fields["status"], "filled")
        self.assertNotIn("qty", fields)

    async def test_backfills_price_from_notional_qty(self):
        agent = ExecutionAgent(DummyEventBus(), broker=None)
        order = types.SimpleNamespace(qty=4, filled_avg_price=None, notional=20, status="")
        fields = agent._order_fields(order)
        self.assertAlmostEqual(fields["filled_avg_price"], 5.0)
        self.assertEqual(fields["status"], "filled")
        self.assertNotIn("qty", fields)

    async def test_handles_missing_numbers(self):
        agent = ExecutionAgent(DummyEventBus(), broker=None)
        order = types.SimpleNamespace(qty=None, filled_avg_price=None, notional=None, status=None)
        fields = agent._order_fields(order)
        self.assertIsNone(fields["filled_avg_price"])
        self.assertEqual(fields["status"], "filled")
        self.assertNotIn("qty", fields)


if __name__ == "__main__":
    unittest.main()
