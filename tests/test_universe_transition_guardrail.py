"""
Guardrail test for destructive universe transitions.

Marked as expected failure until a transition manager exists that tears
down and rebuilds universe-bound components; hot toggles must fail.
"""
import unittest
from universe import Universe, UniverseContext


class TestUniverseTransitionGuardrail(unittest.TestCase):
    def test_hot_toggle_universe_fails(self):
        """
        Changing universe at runtime without teardown must be rejected.
        Expect an error when attempting a hot toggle.
        """
        from server.state import AppState

        state = AppState.instance()
        state.set_universe(Universe.SIMULATION)
        original_session = state.universe_context.session_id
        # Seed universe-bound components to ensure teardown
        state.broker = object()
        state.coordinator = object()
        state.analytics_store = object()
        state.websockets = ["stub"]

        # Attempt to hot-toggle to live should raise once enforced
        ctx = state.set_universe(Universe.LIVE)
        self.assertNotEqual(original_session, ctx.session_id)
        self.assertEqual(ctx.universe, Universe.LIVE)
        # Universe-bound components cleared
        self.assertIsNone(state.broker)
        self.assertIsNone(state.coordinator)
        self.assertIsNone(state.analytics_store)
        self.assertEqual(state.websockets, [])


if __name__ == "__main__":
    unittest.main()
