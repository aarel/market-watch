"""
Tests for destructive universe transition manager rebuild.

Verifies that set_universe + rebuild_for_universe tears down old
components and rebuilds new ones with a fresh session_id using injected
factories (no external calls).
"""
import unittest

from server.state import AppState
from universe import Universe


class TestTransitionManager(unittest.TestCase):
    def test_rebuild_creates_fresh_components(self):
        state = AppState.instance()
        # Seed prior components
        state.broker = "old_broker"
        state.coordinator = "old_coordinator"
        state.analytics_store = "old_store"
        state.websockets = ["old_ws"]
        state.set_universe(Universe.SIMULATION)
        old_session = state.universe_context.session_id

        # Factories to track invocations
        brokers = []
        stores = []
        coords = []

        def broker_factory(universe):
            brokers.append(universe)
            return f"broker_{universe.value}"

        def analytics_factory(universe):
            stores.append(universe)
            return f"store_{universe.value}"

        def coordinator_factory(broker, store):
            coords.append((broker, store))
            return f"coord_{broker}_{store}"

        ctx = state.rebuild_for_universe(
            Universe.LIVE,
            broker_factory=broker_factory,
            coordinator_factory=coordinator_factory,
            analytics_factory=analytics_factory,
        )

        self.assertEqual(brokers, [Universe.LIVE])
        self.assertEqual(stores, [Universe.LIVE])
        self.assertEqual(coords, [(f"broker_live", f"store_live")])
        self.assertEqual(state.broker, "broker_live")
        self.assertEqual(state.analytics_store, "store_live")
        self.assertEqual(state.coordinator, "coord_broker_live_store_live")
        self.assertEqual(state.universe_context.universe, Universe.LIVE)
        self.assertNotEqual(old_session, ctx.session_id)
        # websockets cleared
        self.assertEqual(state.websockets, [])


if __name__ == "__main__":
    unittest.main()
