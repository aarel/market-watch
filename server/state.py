"""Global app state container."""
from datetime import datetime
from typing import Optional

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
        self.broker = None
        self.coordinator = None
        self.analytics_store = None
        self.error = None
        # New context with fresh session_id
        self.universe_context = UniverseContext(universe)
        return self.universe_context
