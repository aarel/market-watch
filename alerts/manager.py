"""Alert manager for evaluating rules and dispatching alerts."""
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from threading import RLock
from collections import deque

from .models import Alert, AlertRule, AlertTrigger, AlertSeverity, ChannelType
from .channels.base import AlertChannel


class AlertManager:
    """
    Manages alert rules and dispatches alerts to channels.

    The manager evaluates rules against events, creates alerts,
    and sends them through registered channels.
    """

    def __init__(self, max_history: int = 100):
        """
        Initialize alert manager.

        Args:
            max_history: Maximum number of alerts to keep in history
        """
        self._rules: Dict[str, AlertRule] = {}
        self._channels: Dict[ChannelType, AlertChannel] = {}
        self._history: deque = deque(maxlen=max_history)
        self._lock = RLock()

    def add_rule(self, rule: AlertRule):
        """
        Add or update an alert rule.

        Args:
            rule: Rule to add/update
        """
        with self._lock:
            self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str):
        """
        Remove an alert rule.

        Args:
            rule_id: ID of rule to remove
        """
        with self._lock:
            self._rules.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """
        Get a rule by ID.

        Args:
            rule_id: Rule identifier

        Returns:
            AlertRule if found, None otherwise
        """
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self) -> List[AlertRule]:
        """
        Get all rules.

        Returns:
            List of all registered rules
        """
        with self._lock:
            return list(self._rules.values())

    def register_channel(self, channel_type: ChannelType, channel: AlertChannel):
        """
        Register a delivery channel.

        Args:
            channel_type: Type of channel
            channel: Channel implementation
        """
        with self._lock:
            self._channels[channel_type] = channel

    def unregister_channel(self, channel_type: ChannelType):
        """
        Unregister a delivery channel.

        Args:
            channel_type: Type of channel to remove
        """
        with self._lock:
            self._channels.pop(channel_type, None)

    async def trigger_alert(
        self,
        trigger_type: AlertTrigger,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: Optional[Dict] = None,
    ) -> List[Alert]:
        """
        Trigger alert evaluation and delivery.

        Evaluates all rules, creates alerts for matching rules,
        and dispatches to appropriate channels.

        Args:
            trigger_type: Type of event that occurred
            severity: Severity of the event
            title: Short alert title
            message: Detailed alert message
            context: Additional context data

        Returns:
            List of alerts that were created and sent
        """
        context = context or {}
        alerts_sent = []

        with self._lock:
            # Find matching rules
            matching_rules = [
                rule for rule in self._rules.values()
                if rule.matches(trigger_type, severity)
            ]

            # Create and send alert for each matching rule
            for rule in matching_rules:
                alert = Alert(
                    id=str(uuid.uuid4()),
                    rule_id=rule.id,
                    timestamp=datetime.now(),
                    trigger=trigger_type,
                    severity=severity,
                    title=title,
                    message=message,
                    context=context,
                    channels=rule.channels.copy(),
                )

                # Add to history
                self._history.append(alert)

                # Dispatch to channels
                await self._dispatch_alert(alert)
                alerts_sent.append(alert)

        return alerts_sent

    async def _dispatch_alert(self, alert: Alert):
        """
        Dispatch alert to its channels.

        Args:
            alert: Alert to dispatch
        """
        for channel_type in alert.channels:
            channel = self._channels.get(channel_type)
            if not channel:
                error_msg = f"Channel {channel_type.value} not registered"
                alert.delivery_errors.append(error_msg)
                continue

            try:
                alert.delivery_attempts += 1
                success = await channel.send(alert)

                if success and not alert.delivered:
                    alert.delivered = datetime.now()

            except Exception as exc:
                error_msg = f"Failed to send via {channel_type.value}: {exc}"
                alert.delivery_errors.append(error_msg)

    def get_history(self, limit: Optional[int] = None) -> List[Alert]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return (default: all)

        Returns:
            List of recent alerts, newest first
        """
        with self._lock:
            history = list(self._history)
            history.reverse()  # Newest first

            if limit:
                history = history[:limit]

            return history

    def clear_history(self):
        """Clear alert history."""
        with self._lock:
            self._history.clear()


# Global alert manager instance
_manager = AlertManager()


def get_manager() -> AlertManager:
    """Get the global alert manager instance."""
    return _manager
