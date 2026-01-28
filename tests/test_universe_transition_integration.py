"""
Integration tests for universe transition.

Tests the full universe transition flow including:
- Broker rebuild
- Coordinator restart
- Analytics data isolation
- Component teardown
- Fresh context creation
"""
import unittest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime, timezone

from universe import Universe, UniverseContext
from analytics.store import AnalyticsStore
from fake_broker import FakeBroker
from server.state import AppState


class MockBroker:
    """Mock broker that accepts any universe."""
    def __init__(self, universe: Universe):
        self.universe = universe

    def get_account(self):
        return type('Account', (), {
            'equity': 100000.0,
            'cash': 100000.0,
            'buying_power': 100000.0
        })()

    def get_positions(self):
        return []


class MockCoordinator:
    """Mock coordinator for testing."""
    def __init__(self, broker, analytics_store):
        self.broker = broker
        self.analytics_store = analytics_store
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True


class TestUniverseTransitionIntegration(unittest.TestCase):
    """Integration tests for full universe transition flow."""

    def setUp(self):
        """Create test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()

        # Change to temp directory so analytics stores use it
        os.chdir(self.temp_dir)

        Path(self.temp_dir).joinpath("logs", "simulation").mkdir(parents=True, exist_ok=True)
        Path(self.temp_dir).joinpath("logs", "paper").mkdir(parents=True, exist_ok=True)

        # Create fresh AppState for each test
        AppState._instance = None
        self.state = AppState.instance()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        AppState._instance = None

    # ==================== BASIC TRANSITION TESTS ====================

    def test_transition_creates_new_context(self):
        """Test that universe transition creates a new UniverseContext."""
        # Start in SIMULATION
        ctx1 = self.state.set_universe(Universe.SIMULATION)
        self.assertEqual(ctx1.universe, Universe.SIMULATION)
        session_id_1 = ctx1.session_id

        # Transition to PAPER
        ctx2 = self.state.set_universe(Universe.PAPER)
        self.assertEqual(ctx2.universe, Universe.PAPER)
        session_id_2 = ctx2.session_id

        # Should have different session IDs
        self.assertNotEqual(session_id_1, session_id_2)

        # Context should be updated
        self.assertEqual(self.state.universe_context, ctx2)

    def test_transition_clears_broker(self):
        """Test that universe transition clears the broker."""
        self.state.broker = "fake_broker_instance"
        self.assertIsNotNone(self.state.broker)

        self.state.set_universe(Universe.SIMULATION)

        # Broker should be cleared after transition
        self.assertIsNone(self.state.broker)

    def test_transition_clears_coordinator(self):
        """Test that universe transition clears the coordinator."""
        self.state.coordinator = "fake_coordinator_instance"
        self.assertIsNotNone(self.state.coordinator)

        self.state.set_universe(Universe.SIMULATION)

        # Coordinator should be cleared after transition
        self.assertIsNone(self.state.coordinator)

    def test_transition_clears_analytics_store(self):
        """Test that universe transition clears the analytics store."""
        self.state.analytics_store = "fake_store_instance"
        self.assertIsNotNone(self.state.analytics_store)

        self.state.set_universe(Universe.SIMULATION)

        # Analytics store should be cleared after transition
        self.assertIsNone(self.state.analytics_store)

    # ==================== REBUILD TESTS ====================

    def test_rebuild_creates_components(self):
        """Test that rebuild_for_universe creates broker, coordinator, and analytics."""
        def broker_factory(universe):
            return MockBroker(universe)

        def coordinator_factory(broker, store):
            return MockCoordinator(broker, store)

        def analytics_factory(universe):
            return AnalyticsStore(universe)

        ctx = self.state.rebuild_for_universe(
            Universe.SIMULATION,
            broker_factory=broker_factory,
            coordinator_factory=coordinator_factory,
            analytics_factory=analytics_factory
        )

        # Verify context
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.universe, Universe.SIMULATION)

        # Verify components created
        self.assertIsNotNone(self.state.broker)
        self.assertIsInstance(self.state.broker, MockBroker)
        self.assertEqual(self.state.broker.universe, Universe.SIMULATION)

        self.assertIsNotNone(self.state.coordinator)
        self.assertIsInstance(self.state.coordinator, MockCoordinator)

        self.assertIsNotNone(self.state.analytics_store)
        self.assertIsInstance(self.state.analytics_store, AnalyticsStore)
        self.assertEqual(self.state.analytics_store.universe, Universe.SIMULATION)

    def test_rebuild_calls_teardown(self):
        """Test that rebuild_for_universe calls teardown callback."""
        teardown_called = []

        def teardown_callback(broker, coordinator, store):
            teardown_called.append({
                "broker": broker,
                "coordinator": coordinator,
                "store": store
            })

        # Set up initial components
        self.state.broker = "old_broker"
        self.state.coordinator = "old_coordinator"
        self.state.analytics_store = "old_store"

        # Rebuild with teardown
        self.state.rebuild_for_universe(
            Universe.SIMULATION,
            teardown=teardown_callback
        )

        # Verify teardown was called with old components
        self.assertEqual(len(teardown_called), 1)
        self.assertEqual(teardown_called[0]["broker"], "old_broker")
        self.assertEqual(teardown_called[0]["coordinator"], "old_coordinator")
        self.assertEqual(teardown_called[0]["store"], "old_store")

    # ==================== DATA ISOLATION TESTS ====================

    def test_transition_isolates_analytics_data(self):
        """Test that transitioning universes isolates analytics data."""
        # Create SIMULATION analytics and record data
        sim_store = AnalyticsStore(Universe.SIMULATION)
        sim_store.record_equity({
            "session_id": "sim_session",
            "equity": 100000
        })
        sim_store.record_trade({
            "session_id": "sim_session",
            "symbol": "SIM_STOCK",
            "side": "buy"
        })

        # Load SIMULATION data
        sim_equity = sim_store.load_equity(period="all")
        sim_trades = sim_store.load_trades(period="all")
        self.assertEqual(len(sim_equity), 1)
        self.assertEqual(len(sim_trades), 1)

        # Create PAPER analytics and record different data
        paper_store = AnalyticsStore(Universe.PAPER)
        paper_store.record_equity({
            "session_id": "paper_session",
            "equity": 50000
        })
        paper_store.record_trade({
            "session_id": "paper_session",
            "symbol": "PAPER_STOCK",
            "side": "sell"
        })

        # Load PAPER data
        paper_equity = paper_store.load_equity(period="all")
        paper_trades = paper_store.load_trades(period="all")
        self.assertEqual(len(paper_equity), 1)
        self.assertEqual(len(paper_trades), 1)

        # Verify isolation - PAPER shouldn't see SIMULATION data
        self.assertEqual(paper_equity[0]["equity"], 50000)
        self.assertEqual(paper_trades[0]["symbol"], "PAPER_STOCK")
        self.assertNotIn("SIM_STOCK", [t["symbol"] for t in paper_trades])

        # Verify isolation - SIMULATION shouldn't see PAPER data
        sim_equity_reload = sim_store.load_equity(period="all")
        sim_trades_reload = sim_store.load_trades(period="all")
        self.assertEqual(sim_equity_reload[0]["equity"], 100000)
        self.assertEqual(sim_trades_reload[0]["symbol"], "SIM_STOCK")
        self.assertNotIn("PAPER_STOCK", [t["symbol"] for t in sim_trades_reload])

    def test_transition_preserves_old_universe_data(self):
        """Test that transitioning to a new universe preserves old universe data."""
        # Record SIMULATION data
        sim_store = AnalyticsStore(Universe.SIMULATION)
        sim_store.record_equity({
            "session_id": "sim_session",
            "equity": 100000
        })

        # Transition to PAPER (create new store)
        paper_store = AnalyticsStore(Universe.PAPER)
        paper_store.record_equity({
            "session_id": "paper_session",
            "equity": 50000
        })

        # Old SIMULATION data should still exist
        sim_equity = sim_store.load_equity(period="all")
        self.assertEqual(len(sim_equity), 1)
        self.assertEqual(sim_equity[0]["equity"], 100000)

    def test_fresh_universe_starts_empty(self):
        """Test that a fresh universe starts with empty analytics."""
        # Create new PAPER store (no data yet)
        paper_store = AnalyticsStore(Universe.PAPER)

        # Should have no data
        equity = paper_store.load_equity(period="all")
        trades = paper_store.load_trades(period="all")
        self.assertEqual(len(equity), 0)
        self.assertEqual(len(trades), 0)

    # ==================== FULL INTEGRATION TESTS ====================

    def test_full_transition_flow(self):
        """Test complete universe transition flow from SIMULATION to PAPER."""
        # Track teardown calls
        teardown_log = []

        def teardown_callback(broker, coordinator, store):
            teardown_log.append({
                "broker_universe": getattr(broker, "universe", None),
                "coordinator": coordinator,
                "store_universe": getattr(store, "universe", None)
            })

        # Phase 1: Start in SIMULATION
        def broker_factory(universe):
            return MockBroker(universe)

        def coordinator_factory(broker, store):
            return MockCoordinator(broker, store)

        def analytics_factory(universe):
            return AnalyticsStore(universe)

        sim_ctx = self.state.rebuild_for_universe(
            Universe.SIMULATION,
            broker_factory=broker_factory,
            coordinator_factory=coordinator_factory,
            analytics_factory=analytics_factory
        )

        # Verify SIMULATION setup
        self.assertEqual(sim_ctx.universe, Universe.SIMULATION)
        self.assertEqual(self.state.broker.universe, Universe.SIMULATION)
        self.assertEqual(self.state.analytics_store.universe, Universe.SIMULATION)

        # Record SIMULATION data
        self.state.analytics_store.record_equity({
            "session_id": sim_ctx.session_id,
            "equity": 100000
        })

        # Store reference to old components
        old_broker = self.state.broker
        old_coordinator = self.state.coordinator
        old_store = self.state.analytics_store

        # Phase 2: Transition to PAPER
        paper_ctx = self.state.rebuild_for_universe(
            Universe.PAPER,
            broker_factory=broker_factory,
            coordinator_factory=coordinator_factory,
            analytics_factory=analytics_factory,
            teardown=teardown_callback
        )

        # Verify teardown was called
        self.assertEqual(len(teardown_log), 1)
        self.assertEqual(teardown_log[0]["broker_universe"], Universe.SIMULATION)
        self.assertEqual(teardown_log[0]["store_universe"], Universe.SIMULATION)

        # Verify new PAPER setup
        self.assertEqual(paper_ctx.universe, Universe.PAPER)
        self.assertEqual(self.state.broker.universe, Universe.PAPER)
        self.assertEqual(self.state.analytics_store.universe, Universe.PAPER)

        # Verify different session IDs
        self.assertNotEqual(sim_ctx.session_id, paper_ctx.session_id)

        # Verify new components (not same instances)
        self.assertIsNot(self.state.broker, old_broker)
        self.assertIsNot(self.state.coordinator, old_coordinator)
        self.assertIsNot(self.state.analytics_store, old_store)

        # Verify PAPER analytics starts empty
        paper_equity = self.state.analytics_store.load_equity(period="all")
        self.assertEqual(len(paper_equity), 0)

        # Record PAPER data
        self.state.analytics_store.record_equity({
            "session_id": paper_ctx.session_id,
            "equity": 50000
        })

        # Verify PAPER data exists
        paper_equity = self.state.analytics_store.load_equity(period="all")
        self.assertEqual(len(paper_equity), 1)
        self.assertEqual(paper_equity[0]["equity"], 50000)
        self.assertEqual(paper_equity[0]["universe"], "paper")

        # Verify SIMULATION data still exists (create new store to check)
        sim_store_check = AnalyticsStore(Universe.SIMULATION)
        sim_equity_check = sim_store_check.load_equity(period="all")
        self.assertEqual(len(sim_equity_check), 1)
        self.assertEqual(sim_equity_check[0]["equity"], 100000)
        self.assertEqual(sim_equity_check[0]["universe"], "simulation")

    def test_multiple_transitions(self):
        """Test multiple universe transitions in sequence."""
        def broker_factory(universe):
            return MockBroker(universe)

        def analytics_factory(universe):
            return AnalyticsStore(universe)

        session_ids = []

        # SIMULATION → PAPER → SIMULATION → PAPER
        for universe in [Universe.SIMULATION, Universe.PAPER, Universe.SIMULATION, Universe.PAPER]:
            ctx = self.state.rebuild_for_universe(
                universe,
                broker_factory=broker_factory,
                analytics_factory=analytics_factory
            )
            session_ids.append(ctx.session_id)

            # Verify correct universe
            self.assertEqual(self.state.broker.universe, universe)
            self.assertEqual(self.state.analytics_store.universe, universe)

        # All session IDs should be unique
        self.assertEqual(len(set(session_ids)), 4)

    def test_transition_with_broker_validation(self):
        """Test that transition enforces broker universe constraints."""
        # Attempting to create SIMULATION broker should work
        def sim_broker_factory(universe):
            return FakeBroker(universe=universe)

        ctx = self.state.rebuild_for_universe(
            Universe.SIMULATION,
            broker_factory=sim_broker_factory
        )

        self.assertEqual(self.state.broker.universe, Universe.SIMULATION)

        # FakeBroker should reject PAPER universe
        def paper_broker_factory(universe):
            # This will raise ValueError if universe is not SIMULATION
            return FakeBroker(universe=universe)

        # This should raise because FakeBroker only accepts SIMULATION
        with self.assertRaises(ValueError):
            self.state.rebuild_for_universe(
                Universe.PAPER,
                broker_factory=paper_broker_factory
            )


class TestUniverseTransitionEdgeCases(unittest.TestCase):
    """Edge case tests for universe transition."""

    def setUp(self):
        """Create test environment."""
        AppState._instance = None
        self.state = AppState.instance()

    def tearDown(self):
        """Clean up."""
        AppState._instance = None

    def test_transition_without_existing_components(self):
        """Test transitioning when no components exist yet."""
        # Should not crash when nothing exists
        ctx = self.state.set_universe(Universe.SIMULATION)

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.universe, Universe.SIMULATION)
        self.assertIsNone(self.state.broker)
        self.assertIsNone(self.state.coordinator)
        self.assertIsNone(self.state.analytics_store)

    def test_rebuild_with_null_factories(self):
        """Test rebuild_for_universe with no factories provided."""
        # Should use defaults (return None)
        ctx = self.state.rebuild_for_universe(Universe.SIMULATION)

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.universe, Universe.SIMULATION)

        # Components should be None (default factory returns None)
        self.assertIsNone(self.state.broker)
        self.assertIsNone(self.state.coordinator)
        self.assertIsNone(self.state.analytics_store)

    def test_teardown_with_none_components(self):
        """Test that teardown handles None components gracefully."""
        teardown_called = []

        def teardown_callback(broker, coordinator, store):
            teardown_called.append({
                "broker": broker,
                "coordinator": coordinator,
                "store": store
            })

        # Components are None by default
        self.state.rebuild_for_universe(
            Universe.SIMULATION,
            teardown=teardown_callback
        )

        # Teardown should be called even with None components
        self.assertEqual(len(teardown_called), 1)
        self.assertIsNone(teardown_called[0]["broker"])
        self.assertIsNone(teardown_called[0]["coordinator"])
        self.assertIsNone(teardown_called[0]["store"])


if __name__ == "__main__":
    unittest.main()
