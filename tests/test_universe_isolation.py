"""Tests for universe isolation invariants.

These tests validate that the universe isolation system enforces
critical safety invariants through the type system and runtime checks.
"""
import unittest

from agents.event_bus import EventBus
from agents.events import LogEvent, MarketDataReady
from universe import Universe, UniverseContext


class TestUniverseIsolationInvariants(unittest.IsolatedAsyncioTestCase):
    """Test strict universe isolation enforcement."""

    def test_event_bus_requires_universe_context(self):
        """EventBus cannot be created without UniverseContext."""
        with self.assertRaises(TypeError) as ctx:
            EventBus(None)

        self.assertIn("UniverseContext", str(ctx.exception))
        self.assertIn("requires", str(ctx.exception).lower())

    async def test_event_bus_rejects_wrong_universe(self):
        """EventBus rejects events from different universe."""
        # Create EventBus for SIMULATION
        sim_context = UniverseContext(Universe.SIMULATION)
        sim_bus = EventBus(sim_context)

        # Create EventBus for PAPER
        paper_context = UniverseContext(Universe.PAPER)
        paper_bus = EventBus(paper_context)

        # Create event for PAPER universe
        paper_event = LogEvent(
            universe=paper_context.universe,
            session_id=paper_context.session_id,
            source="test",
            level="info",
            message="test message"
        )

        # Paper bus should accept it
        await paper_bus.publish(paper_event)

        # Simulation bus should reject it
        with self.assertRaises(ValueError) as ctx:
            await sim_bus.publish(paper_event)

        self.assertIn("universe mismatch", str(ctx.exception).lower())
        self.assertIn(Universe.PAPER.value, str(ctx.exception))
        self.assertIn(Universe.SIMULATION.value, str(ctx.exception))

    async def test_event_bus_rejects_missing_session_id(self):
        """EventBus rejects events without session_id."""
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)

        # Try to create event with empty session_id
        event = LogEvent(
            universe=context.universe,
            session_id="",  # Empty session_id
            source="test",
            level="info",
            message="test"
        )

        # Should reject empty session_id
        with self.assertRaises(ValueError) as ctx:
            await bus.publish(event)

        self.assertIn("session_id", str(ctx.exception).lower())

    def test_event_requires_universe_at_construction(self):
        """Events cannot be created without universe."""
        context = UniverseContext(Universe.SIMULATION)

        # This should work - all required fields provided
        event = LogEvent(
            universe=context.universe,
            session_id=context.session_id,
            source="test",
            level="info",
            message="test"
        )
        self.assertEqual(event.universe, Universe.SIMULATION)
        self.assertEqual(event.session_id, context.session_id)

        # This should fail - missing required universe
        with self.assertRaises(TypeError):
            LogEvent(
                session_id=context.session_id,
                source="test",
                level="info",
                message="test"
            )

        # This should fail - missing required session_id
        with self.assertRaises(TypeError):
            LogEvent(
                universe=context.universe,
                source="test",
                level="info",
                message="test"
            )

    def test_universe_context_generates_session_id(self):
        """UniverseContext automatically generates session_id."""
        context1 = UniverseContext(Universe.SIMULATION)
        context2 = UniverseContext(Universe.SIMULATION)

        # Each context should have unique session_id
        self.assertIsNotNone(context1.session_id)
        self.assertIsNotNone(context2.session_id)
        self.assertNotEqual(context1.session_id, context2.session_id)

        # Session IDs should have proper format
        self.assertTrue(context1.session_id.startswith("session_"))
        self.assertTrue(context2.session_id.startswith("session_"))

    def test_universe_enum_values(self):
        """Universe enum has expected values."""
        self.assertEqual(Universe.LIVE.value, "live")
        self.assertEqual(Universe.PAPER.value, "paper")
        self.assertEqual(Universe.SIMULATION.value, "simulation")

        # All three universes should be distinct
        self.assertNotEqual(Universe.LIVE, Universe.PAPER)
        self.assertNotEqual(Universe.LIVE, Universe.SIMULATION)
        self.assertNotEqual(Universe.PAPER, Universe.SIMULATION)

    async def test_event_bus_validates_universe_type(self):
        """EventBus validates universe is proper enum."""
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)

        # Valid event with proper Universe enum
        valid_event = LogEvent(
            universe=context.universe,
            session_id=context.session_id,
            source="test",
            level="info",
            message="test"
        )

        # Should succeed
        await bus.publish(valid_event)

        # Event with wrong universe should fail
        wrong_event = LogEvent(
            universe=Universe.LIVE,  # Different universe
            session_id=context.session_id,
            source="test",
            level="info",
            message="test"
        )

        with self.assertRaises(ValueError) as ctx:
            await bus.publish(wrong_event)

        self.assertIn("universe mismatch", str(ctx.exception).lower())

    async def test_cross_universe_contamination_prevented(self):
        """Events from one universe cannot leak into another."""
        # Create separate contexts and buses
        sim_context = UniverseContext(Universe.SIMULATION)
        sim_bus = EventBus(sim_context)

        paper_context = UniverseContext(Universe.PAPER)
        paper_bus = EventBus(paper_context)

        # Track events published to each bus
        sim_events = []
        paper_events = []

        sim_bus.subscribe_all(sim_events.append)
        paper_bus.subscribe_all(paper_events.append)

        # Publish simulation event
        sim_event = LogEvent(
            universe=sim_context.universe,
            session_id=sim_context.session_id,
            source="test",
            level="info",
            message="sim message"
        )
        await sim_bus.publish(sim_event)

        # Publish paper event
        paper_event = LogEvent(
            universe=paper_context.universe,
            session_id=paper_context.session_id,
            source="test",
            level="info",
            message="paper message"
        )
        await paper_bus.publish(paper_event)

        # Verify isolation
        self.assertEqual(len(sim_events), 1)
        self.assertEqual(len(paper_events), 1)
        self.assertEqual(sim_events[0].universe, Universe.SIMULATION)
        self.assertEqual(paper_events[0].universe, Universe.PAPER)

        # Try to publish paper event to sim bus (should fail)
        with self.assertRaises(ValueError):
            await sim_bus.publish(paper_event)

        # Sim bus should still only have 1 event
        self.assertEqual(len(sim_events), 1)

    def test_universe_context_immutability(self):
        """UniverseContext universe and session_id are immutable."""
        context = UniverseContext(Universe.SIMULATION)
        original_universe = context.universe
        original_session_id = context.session_id

        # Attempting to modify should fail
        with self.assertRaises(AttributeError):
            context.universe = Universe.LIVE

        with self.assertRaises(AttributeError):
            context.session_id = "hacked_session"

        # Values should remain unchanged
        self.assertEqual(context.universe, original_universe)
        self.assertEqual(context.session_id, original_session_id)


class TestEventProvenanceRequirements(unittest.TestCase):
    """Test that all events have proper provenance."""

    def test_market_data_ready_requires_provenance(self):
        """MarketDataReady event requires universe and session_id."""
        context = UniverseContext(Universe.SIMULATION)

        # Should succeed with all fields
        event = MarketDataReady(
            universe=context.universe,
            session_id=context.session_id,
            source="test",
            symbols=["AAPL"],
            prices={"AAPL": 100.0},
            bars={},
            account={},
            positions=[],
            market_open=True
        )
        self.assertIsNotNone(event.universe)
        self.assertIsNotNone(event.session_id)

        # Should fail without universe
        with self.assertRaises(TypeError):
            MarketDataReady(
                session_id=context.session_id,
                source="test",
                symbols=["AAPL"],
                prices={"AAPL": 100.0},
                bars={},
                account={},
                positions=[],
                market_open=True
            )

        # Should fail without session_id
        with self.assertRaises(TypeError):
            MarketDataReady(
                universe=context.universe,
                source="test",
                symbols=["AAPL"],
                prices={"AAPL": 100.0},
                bars={},
                account={},
                positions=[],
                market_open=True
            )


if __name__ == "__main__":
    unittest.main()
