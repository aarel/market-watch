"""Coordinator - orchestrates all agents."""
from typing import TYPE_CHECKING, Callable, Optional

from .event_bus import EventBus
from .data_agent import DataAgent
from .signal_agent import SignalAgent
from .risk_agent import RiskAgent
from .execution_agent import ExecutionAgent
from .monitor_agent import MonitorAgent
from .alert_agent import AlertAgent
from .observability_agent import ObservabilityAgent
from .test_agent import TestAgent
from .replay_recorder_agent import ReplayRecorderAgent
from .ui_check_agent import UICheckAgent
from .session_logger_agent import SessionLoggerAgent
from .events import StopLossTriggered, RiskCheckPassed, LogEvent
from strategies import get_strategy
from universe import Universe, UniverseContext
import config

if TYPE_CHECKING:
    from broker import AlpacaBroker


class Coordinator:
    """Manages all agents and their lifecycle."""

    def __init__(self, broker: "AlpacaBroker", analytics_store=None, universe: Universe = None):
        """
        Initialize coordinator.

        Args:
            broker: Broker instance
            analytics_store: Optional analytics store
            universe: Execution universe (REQUIRED - no implicit universe allowed)
        """
        if universe is None:
            raise TypeError(
                "Coordinator requires explicit universe parameter. "
                "No implicit universe inference allowed per design contract."
            )

        self.broker = broker

        # Create universe context (required for EventBus)
        self.context = UniverseContext(universe)
        self.universe = universe
        self.session_id = self.context.session_id

        # Create event bus with required context
        self.event_bus = EventBus(self.context)

        # Startup logs (now we have universe and session_id)
        self._startup_logs = []

        # Create strategy instance from config
        try:
            strategy = get_strategy(
                config.STRATEGY,
                lookback_days=config.LOOKBACK_DAYS,
                momentum_threshold=config.MOMENTUM_THRESHOLD,
                sell_threshold=config.SELL_THRESHOLD,
                stop_loss_pct=config.STOP_LOSS_PCT,
            )
            self._startup_logs.append(LogEvent(
                universe=self.universe,
                session_id=self.session_id,
                source="Coordinator",
                level="info",
                message=f"Loaded strategy '{strategy.name}'"
            ))
        except ValueError:
            self._startup_logs.append(LogEvent(
                universe=self.universe,
                session_id=self.session_id,
                source="Coordinator",
                level="warning",
                message=f"Invalid strategy '{config.STRATEGY}', falling back to momentum"
            ))
            from strategies import MomentumStrategy
            strategy = MomentumStrategy()

        # Initialize all agents
        self.data_agent = DataAgent(
            self.event_bus,
            broker,
            interval_minutes=config.TRADE_INTERVAL_MINUTES,
        )
        self.signal_agent = SignalAgent(self.event_bus, broker, strategy=strategy)
        self.risk_agent = RiskAgent(self.event_bus, broker)
        self.execution_agent = ExecutionAgent(self.event_bus, broker, self.risk_agent)
        self.monitor_agent = MonitorAgent(self.event_bus, broker, check_interval_seconds=120)
        self.alert_agent = AlertAgent(self.event_bus)
        self.observability_agent = None
        self.analytics_agent = None
        self.test_agent = None
        self.replay_recorder_agent = None
        self.ui_check_agent = None
        self.session_logger_agent = None
        if config.OBSERVABILITY_ENABLED:
            self.observability_agent = ObservabilityAgent(
                self.event_bus,
                log_path=config.OBSERVABILITY_LOG_PATH,
                max_log_mb=config.OBSERVABILITY_MAX_LOG_MB,
            )
        if analytics_store and getattr(config, "ANALYTICS_ENABLED", True):
            from .analytics_agent import AnalyticsAgent
            self.analytics_agent = AnalyticsAgent(self.event_bus, broker, analytics_store)
        if getattr(config, "TEST_AGENT_ENABLED", False):
            self.test_agent = TestAgent(
                self.event_bus,
                interval_minutes=config.TEST_AGENT_INTERVAL_MINUTES,
                log_path=config.TEST_AGENT_LOG_PATH,
            )
        if getattr(config, "REPLAY_RECORDER_ENABLED", False):
            symbols = config.REPLAY_RECORDER_SYMBOLS or config.WATCHLIST
            self.replay_recorder_agent = ReplayRecorderAgent(
                self.event_bus,
                broker,
                interval_minutes=config.REPLAY_RECORDER_INTERVAL_MINUTES,
                symbols=symbols,
            )
        if getattr(config, "UI_CHECK_ENABLED", False):
            url = config.UI_CHECK_URL or f"http://{config.API_HOST}:{config.UI_PORT}"
            self.ui_check_agent = UICheckAgent(
                self.event_bus,
                interval_minutes=config.UI_CHECK_INTERVAL_MINUTES,
                url=url,
                log_path=config.UI_CHECK_LOG_PATH,
            )
        if True:  # session logger always on; low overhead
            self.session_logger_agent = SessionLoggerAgent(
                self.event_bus,
                broker,
                interval_minutes=10,
                log_path="logs/observability/sessions.jsonl",
            )

        # Wire up stop-loss triggers to execution
        self.event_bus.subscribe(StopLossTriggered, self._handle_stop_loss)

        self._running = False

    async def _handle_stop_loss(self, event: StopLossTriggered):
        """Convert stop-loss event to a sell execution."""
        # Create a risk-passed event for the execution agent
        sell_event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.session_id,
            source="MonitorAgent",
            symbol=event.symbol,
            action="sell",
            trade_value=event.position_value,
            position_pct=0,
            reason=f"Stop loss triggered at {event.loss_pct:.1%} loss",
        )
        await self.event_bus.publish(sell_event)

    async def start(self):
        """Start all agents."""
        self._running = True

        # Publish startup logs
        for log_event in self._startup_logs:
            await self.event_bus.publish(log_event)
        self._startup_logs.clear()

        await self.data_agent.start()
        await self.signal_agent.start()
        await self.risk_agent.start()
        await self.execution_agent.start()
        await self.monitor_agent.start()
        await self.alert_agent.start()
        if self.observability_agent:
            await self.observability_agent.start()
        if self.analytics_agent:
            await self.analytics_agent.start()
        if self.test_agent:
            await self.test_agent.start()
        if self.replay_recorder_agent:
            await self.replay_recorder_agent.start()
        if self.ui_check_agent:
            await self.ui_check_agent.start()
        if self.session_logger_agent:
            await self.session_logger_agent.start()

        # Trigger initial data fetch
        await self.data_agent.fetch_data()

    async def stop(self):
        """Stop all agents."""
        self._running = False
        await self.event_bus.publish(LogEvent(
            universe=self.universe,
            session_id=self.session_id,
            source="Coordinator",
            level="info",
            message="Bot shutting down."
        ))

    def set_broadcast_callback(self, callback: Callable):
        """Set WebSocket broadcast callback for alert agent."""
        self.alert_agent.set_broadcast_callback(callback)

    async def manual_trade(self, symbol: str, action: str, amount: float = None, qty: float = None, mode: str = "notional") -> dict:
        """Execute a manual trade."""
        return await self.execution_agent.execute_manual_trade(symbol, action, amount, qty, mode)

    async def refresh_data(self):
        """Manually trigger a data refresh."""
        await self.data_agent.fetch_data()

    def update_trade_interval(self, interval_minutes: int):
        """Update the data fetch interval in minutes."""
        if interval_minutes <= 0:
            raise ValueError("Trade interval must be positive")
        self.data_agent.interval_minutes = interval_minutes

    def get_signals(self):
        """Get current signals from signal agent."""
        return self.signal_agent.get_signals()

    def get_logs(self, count: int = 50):
        """Get recent log entries."""
        return self.alert_agent.get_logs(count)

    def get_top_gainers(self) -> list[dict]:
        """Get latest top gainers list."""
        return self.data_agent.get_cached_data().get("top_gainers", [])

    def get_market_indices(self) -> list[dict]:
        """Get latest market index proxy list."""
        return self.data_agent.get_cached_data().get("market_indices", [])

    def status(self) -> dict:
        """Get status of all agents."""
        return {
            "running": self._running,
            "agents": {
                "data": self.data_agent.status(),
                "signal": self.signal_agent.status(),
                "risk": self.risk_agent.status(),
                "execution": self.execution_agent.status(),
                "monitor": self.monitor_agent.status(),
                "alert": self.alert_agent.status(),
                "observability": self.observability_agent.status() if self.observability_agent else {"enabled": False},
                "analytics": self.analytics_agent.status() if self.analytics_agent else {"enabled": False},
                "test": self.test_agent.status() if self.test_agent else {"enabled": False},
                "replay_recorder": self.replay_recorder_agent.status() if self.replay_recorder_agent else {"enabled": False},
                "ui_check": self.ui_check_agent.status() if self.ui_check_agent else {"enabled": False},
                "session_logger": self.session_logger_agent.status() if self.session_logger_agent else {"enabled": False},
            }
        }

    def reset_circuit_breaker(self) -> dict:
        """Reset the risk circuit breaker."""
        self.risk_agent.reset_circuit_breaker()
        return self.risk_agent.circuit_breaker.status()
