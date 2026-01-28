"""Global app state container."""
from datetime import datetime
from typing import Optional

from .config_manager import ConfigManager


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

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = AppState()
        return cls._instance
