"""Data models for alert system."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertTrigger(Enum):
    """Types of events that can trigger alerts."""
    ANOMALY_DETECTED = "anomaly_detected"
    CIRCUIT_BREAKER = "circuit_breaker"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MAX_DRAWDOWN = "max_drawdown"
    ORDER_FAILED = "order_failed"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


class ChannelType(Enum):
    """Alert delivery channel types."""
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """
    Configuration for when and how to send alerts.

    Attributes:
        id: Unique rule identifier
        name: Human-readable rule name
        trigger: What event triggers this alert
        severity: Minimum severity level to trigger
        channels: Which channels to send to (email, webhook, etc.)
        enabled: Whether this rule is active
        conditions: Optional dict of trigger-specific conditions
    """
    id: str
    name: str
    trigger: AlertTrigger
    severity: AlertSeverity
    channels: list[ChannelType]
    enabled: bool = True
    conditions: dict[str, Any] = field(default_factory=dict)

    def matches(self, event_type: AlertTrigger, event_severity: AlertSeverity) -> bool:
        """Check if this rule should fire for the given event."""
        if not self.enabled:
            return False

        if self.trigger != event_type:
            return False

        # Check severity - trigger if event severity >= rule severity
        severity_order = {
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }

        return severity_order[event_severity] >= severity_order[self.severity]


@dataclass
class Alert:
    """
    An instance of an alert to be delivered.

    Attributes:
        id: Unique alert identifier
        rule_id: ID of rule that triggered this alert
        timestamp: When alert was created
        trigger: What triggered the alert
        severity: Alert severity level
        title: Short alert title
        message: Detailed alert message
        context: Additional context data
        channels: Which channels to deliver to
        delivered: Timestamp when delivered (None if pending)
        delivery_attempts: Number of delivery attempts
        delivery_errors: List of delivery error messages
    """
    id: str
    rule_id: str
    timestamp: datetime
    trigger: AlertTrigger
    severity: AlertSeverity
    title: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    channels: list[ChannelType] = field(default_factory=list)
    delivered: datetime | None = None
    delivery_attempts: int = 0
    delivery_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "timestamp": self.timestamp.isoformat(),
            "trigger": self.trigger.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "context": self.context,
            "channels": [ch.value for ch in self.channels],
            "delivered": self.delivered.isoformat() if self.delivered else None,
            "delivery_attempts": self.delivery_attempts,
            "delivery_errors": self.delivery_errors,
        }
