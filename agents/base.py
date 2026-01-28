"""Base agent class."""
import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event_bus import EventBus
    from universe import Universe


class BaseAgent(ABC):
    """
    Base class for all agents.

    All agents receive their universe context from the EventBus.
    This ensures consistent provenance across all events.
    """

    def __init__(self, name: str, event_bus: "EventBus"):
        self.name = name
        self.event_bus = event_bus
        self.running = False
        self._task = None

        # Extract universe context from event bus
        # All events created by this agent must use these
        self.universe = event_bus._context.universe
        self.session_id = event_bus._context.session_id

    @abstractmethod
    async def start(self):
        """Start the agent."""
        self.running = True

    @abstractmethod
    async def stop(self):
        """Stop the agent."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def status(self) -> dict:
        """Get agent status."""
        return {
            "name": self.name,
            "running": self.running,
        }
