"""Base interface for alert delivery channels."""
from abc import ABC, abstractmethod
from typing import Any

from ..models import Alert


class AlertChannel(ABC):
    """
    Base class for alert delivery channels.

    Channels handle the actual delivery of alerts through various
    mechanisms (email, webhook, SMS, etc.).
    """

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send an alert through this channel.

        Args:
            alert: The alert to send

        Returns:
            True if delivery succeeded, False otherwise

        Raises:
            Exception: On delivery failure (will be caught and logged by manager)
        """
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate channel configuration.

        Args:
            config: Channel-specific configuration dict

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid with explanation
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get human-readable channel name."""
        pass
