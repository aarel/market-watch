"""
Guardrail tests for broker universe enforcement.

Marked as expected failures until broker is refactored to require an
explicit universe and to refuse mismatches. They document the desired
behavior so future work can unmark them once implemented.
"""
import unittest

from universe import Universe


class TestBrokerUniverseGuardrail(unittest.TestCase):
    def test_broker_requires_universe_argument(self):
        """
        A broker must not be constructible without an explicit universe.
        This prevents silent defaults and mode toggles.
        """
        from broker import AlpacaBroker
        with self.assertRaises(TypeError):
            AlpacaBroker()  # missing required universe

    def test_live_universe_uses_live_endpoint_only(self):
        """
        Constructing a LIVE broker with a paper/sim endpoint must raise.
        """
        from broker import AlpacaBroker
        with self.assertRaises(ValueError):
            AlpacaBroker(universe=Universe.LIVE, base_url="https://paper-api.alpaca.markets")

    def test_sim_universe_cannot_hit_live_endpoint(self):
        """
        Constructing a SIMULATION broker against live API must raise.
        """
        from broker import AlpacaBroker
        with self.assertRaises(ValueError):
            AlpacaBroker(universe=Universe.SIMULATION, base_url="https://api.alpaca.markets")


if __name__ == "__main__":
    unittest.main()
