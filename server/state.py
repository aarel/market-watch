"""Global app state container."""
from datetime import datetime
from typing import Optional, Callable

from .config_manager import ConfigManager
from universe import Universe, UniverseContext


class AppState:
    _instance = None

    def __init__(self):
        self.broker = None
        self.coordinator = None
        self.websockets = []
        self.error = None
        self.observability = None
        self.observability_error = None
        self.observability_task = None
        self.observability_lock = None
        self.expectations_by_agent = {}
        self.analytics_store = None
        self.start_time = datetime.now()
        self.config_manager = ConfigManager()
        self.universe_context: UniverseContext | None = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = AppState()
        return cls._instance

    def set_universe(self, universe: Universe):
        """
        Destructive universe transition: tears down universe-bound
        components and creates a new UniverseContext.
        """
        # Tear down existing universe-bound components
        self.error = None
        self.websockets = []
        # New context with fresh session_id
        self.universe_context = UniverseContext(universe)
        # Clear components after context creation (order matters for teardown callbacks)
        self.broker = None
        self.coordinator = None
        self.analytics_store = None
        return self.universe_context

    def rebuild_for_universe(
        self,
        universe: Universe,
        broker_factory: Optional[Callable[[Universe], object]] = None,
        coordinator_factory: Optional[Callable[[object, object], object]] = None,
        analytics_factory: Optional[Callable[[Universe], object]] = None,
        teardown: Optional[Callable[[object, object, object], None]] = None,
    ):
        """
        Perform a destructive universe transition and rebuild broker,
        coordinator, and analytics store using provided factories.

        Factories are injectable to allow testing without hitting real
        brokers or external services.
        """
        # Optional teardown of existing components before reset
        if teardown:
            teardown(self.broker, self.coordinator, self.analytics_store)

        ctx = self.set_universe(universe)

        broker_factory = broker_factory or (lambda uni: None)
        analytics_factory = analytics_factory or (lambda uni: None)
        coordinator_factory = coordinator_factory or (lambda broker, store: None)

        self.broker = broker_factory(universe)
        self.analytics_store = analytics_factory(universe)
        self.coordinator = coordinator_factory(self.broker, self.analytics_store)
        return ctx
