"""Tests for config event propagation to agents."""
import asyncio
import unittest

from agents.data_agent import DataAgent
from agents.event_bus import EventBus
from agents.events import ConfigUpdated
from agents.signal_agent import SignalAgent
from server.config_manager import ConfigManager
from strategies import MomentumStrategy
from universe import Universe, UniverseContext


class MockBroker:
    """Mock broker for testing."""
    def is_market_open(self):
        return True

    def get_account(self):
        from types import SimpleNamespace
        return SimpleNamespace(portfolio_value=100000, buying_power=50000, cash=50000, equity=100000)

    def get_positions(self):
        return []

    def get_snapshots(self, symbols):
        return {}

    def get_current_price(self, symbol):
        return 100.0

    def get_bars(self, symbol, days=30):
        return []


class TestConfigPropagation(unittest.IsolatedAsyncioTestCase):
    """Test that config changes propagate to agents via events."""

    async def test_data_agent_updates_interval(self):
        """Test DataAgent updates interval when config changes."""
        context = UniverseContext(Universe.SIMULATION)
        event_bus = EventBus(context)
        broker = MockBroker()

        # Create DataAgent with initial interval
        agent = DataAgent(event_bus, broker, interval_minutes=10)
        await agent.start()

        self.assertEqual(agent.interval_minutes, 10)

        # Emit ConfigUpdated event
        config_event = ConfigUpdated(
            universe=context.universe,
            session_id=context.session_id,
            source="Test",
            changed_keys=["trade_interval"],
            config_snapshot={"trade_interval": 5},
        )

        await event_bus.publish(config_event)
        await asyncio.sleep(0.01)  # Let event propagate

        # Verify interval updated
        self.assertEqual(agent.interval_minutes, 5)

        await agent.stop()

    async def test_signal_agent_updates_strategy_params(self):
        """Test SignalAgent updates strategy parameters when config changes."""
        context = UniverseContext(Universe.SIMULATION)
        event_bus = EventBus(context)
        broker = MockBroker()

        # Create SignalAgent with momentum strategy
        strategy = MomentumStrategy()
        strategy.momentum_threshold = 0.02
        agent = SignalAgent(event_bus, broker, strategy=strategy)
        await agent.start()

        self.assertEqual(agent.strategy.momentum_threshold, 0.02)

        # Update global config
        import config
        config.MOMENTUM_THRESHOLD = 0.05

        # Emit ConfigUpdated event
        config_event = ConfigUpdated(
            universe=context.universe,
            session_id=context.session_id,
            source="Test",
            changed_keys=["momentum_threshold"],
            config_snapshot={"momentum_threshold": 0.05},
        )

        await event_bus.publish(config_event)
        await asyncio.sleep(0.01)  # Let event propagate

        # Verify strategy params updated
        self.assertEqual(agent.strategy.momentum_threshold, 0.05)

        await agent.stop()

    async def test_config_manager_emits_events(self):
        """Test ConfigManager emits ConfigUpdated when apply_updates is called."""
        context = UniverseContext(Universe.SIMULATION)
        event_bus = EventBus(context)

        # Create ConfigManager with event bus
        manager = ConfigManager(universe=Universe.SIMULATION, event_bus=event_bus)

        # Track emitted events
        emitted_events = []

        def capture_event(event: ConfigUpdated):
            emitted_events.append(event)

        event_bus.subscribe(ConfigUpdated, capture_event)

        # Apply config updates
        manager.apply_updates({"trade_interval": 15, "max_daily_trades": 100})

        await asyncio.sleep(0.01)  # Let event propagate

        # Verify event was emitted
        self.assertEqual(len(emitted_events), 1)
        event = emitted_events[0]
        self.assertIn("trade_interval", event.changed_keys)
        self.assertIn("max_daily_trades", event.changed_keys)
        self.assertEqual(event.config_snapshot["trade_interval"], 15)
        self.assertEqual(event.config_snapshot["max_daily_trades"], 100)

    async def test_no_event_when_no_changes(self):
        """Test ConfigManager doesn't emit event when no actual changes occur."""
        context = UniverseContext(Universe.SIMULATION)
        event_bus = EventBus(context)

        manager = ConfigManager(universe=Universe.SIMULATION, event_bus=event_bus)

        emitted_events = []

        def capture_event(event: ConfigUpdated):
            emitted_events.append(event)

        event_bus.subscribe(ConfigUpdated, capture_event)

        # Apply same value (no change)
        current_interval = manager.state.trade_interval
        manager.apply_updates({"trade_interval": current_interval})

        await asyncio.sleep(0.01)

        # Verify no event emitted
        self.assertEqual(len(emitted_events), 0)


if __name__ == '__main__':
    unittest.main()
