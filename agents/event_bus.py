"""Event bus for agent communication."""
import asyncio
from collections import defaultdict
from typing import Callable, Type
from .events import Event
from universe import UniverseContext


class EventBus:
    """
    Pub/sub event bus for agent communication.

    Universe-scoped: Each event bus is bound to a specific universe context.
    All events published must match the bus's universe.

    STRICT ENFORCEMENT: EventBus cannot exist without UniverseContext.
    This makes universe-less execution graphs impossible.
    """

    def __init__(self, context: UniverseContext):
        """
        Create event bus.

        Args:
            context: Universe context (REQUIRED, not optional)

        Raises:
            TypeError: If context is None
        """
        if context is None:
            raise TypeError(
                "EventBus requires UniverseContext. "
                "Universe-less event buses are forbidden for safety. "
                "Create UniverseContext(universe) before creating EventBus."
            )

        self._context = context
        self._subscribers: dict[Type[Event], list[Callable]] = defaultdict(list)
        self._global_subscribers: list[Callable] = []
        self._event_log: list[Event] = []
        self._max_log_size = 100

    def subscribe(self, event_type: Type[Event], handler: Callable):
        """Subscribe to a specific event type."""
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable):
        """Subscribe to all events."""
        self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: Type[Event], handler: Callable):
        """Unsubscribe from an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def unsubscribe_all(self, handler: Callable):
        """Unsubscribe from all events."""
        if handler in self._global_subscribers:
            self._global_subscribers.remove(handler)

    async def publish(self, event: Event):
        """
        Publish an event to all subscribers.

        STRICT ENFORCEMENT: Validates that event universe matches bus universe.
        Events must already have universe and session_id at construction time.

        Raises:
            ValueError: If event universe doesn't match bus universe
        """
        # Validate event universe matches bus universe
        if event.universe != self._context.universe:
            raise ValueError(
                f"Event universe mismatch: event has {event.universe.value}, "
                f"but EventBus expects {self._context.universe.value}. "
                "Events cannot cross universe boundaries."
            )

        # Validate event has session_id
        if not event.session_id:
            raise ValueError(
                f"Event missing session_id. All events must have provenance. "
                f"Event type: {type(event).__name__}"
            )

        # Log the event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Notify type-specific subscribers
        event_type = type(event)
        for handler in self._subscribers[event_type]:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Error in event handler for {event_type.__name__}: {e}")

        # Notify global subscribers
        for handler in self._global_subscribers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Error in global event handler: {e}")

    def get_recent_events(self, count: int = 50) -> list[Event]:
        """Get recent events from the log."""
        return self._event_log[-count:]

    def clear_log(self):
        """Clear the event log."""
        self._event_log = []
