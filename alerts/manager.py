"""Alert manager for evaluating rules and dispatching alerts."""
import json
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path
from threading import RLock

from .channels.base import AlertChannel
from .models import Alert, AlertRule, AlertSeverity, AlertTrigger, ChannelType


class AlertManager:
    """
    Manages alert rules and dispatches alerts to channels.

    The manager evaluates rules against events, creates alerts,
    and sends them through registered channels.

    History is kept in-memory (deque) for fast access and optionally
    persisted to a JSONL file so it survives restarts. Set
    `history_path` to enable persistence.
    """

    def __init__(self, max_history: int = 100, history_path: Path | None = None):
        """
        Initialize alert manager.

        Args:
            max_history: Maximum number of alerts to keep in memory.
            history_path: Optional path to a JSONL file for persistent
                history. When set, each new alert is appended and the
                file is read on first access to pre-populate in-memory
                history.
        """
        self._rules: dict[str, AlertRule] = {}
        self._channels: dict[ChannelType, AlertChannel] = {}
        self._history: deque = deque(maxlen=max_history)
        self._lock = RLock()
        self._history_path: Path | None = history_path
        self._history_loaded: bool = False  # lazy-load on first get_history call

    # ------------------------------------------------------------------
    # Rule management
    # ------------------------------------------------------------------

    def add_rule(self, rule: AlertRule):
        """Add or update an alert rule."""
        with self._lock:
            self._rules[rule.id] = rule

    def remove_rule(self, rule_id: str):
        """Remove an alert rule."""
        with self._lock:
            self._rules.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> AlertRule | None:
        """Get a rule by ID."""
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self) -> list[AlertRule]:
        """Get all registered rules."""
        with self._lock:
            return list(self._rules.values())

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------

    def register_channel(self, channel_type: ChannelType, channel: AlertChannel):
        """Register a delivery channel."""
        with self._lock:
            self._channels[channel_type] = channel

    def unregister_channel(self, channel_type: ChannelType):
        """Unregister a delivery channel."""
        with self._lock:
            self._channels.pop(channel_type, None)

    # ------------------------------------------------------------------
    # Alert dispatch
    # ------------------------------------------------------------------

    async def trigger_alert(
        self,
        trigger_type: AlertTrigger,
        severity: AlertSeverity,
        title: str,
        message: str,
        context: dict | None = None,
    ) -> list[Alert]:
        """
        Trigger alert evaluation and delivery.

        Evaluates all rules, creates alerts for matching rules,
        dispatches to appropriate channels, and persists to JSONL.

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
            matching_rules = [
                rule for rule in self._rules.values()
                if rule.matches(trigger_type, severity)
            ]

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

                self._history.append(alert)
                self._persist_alert(alert)

                await self._dispatch_alert(alert)
                alerts_sent.append(alert)

        return alerts_sent

    async def _dispatch_alert(self, alert: Alert):
        """Dispatch alert to its configured channels."""
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

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self, limit: int | None = None) -> list[Alert]:
        """
        Get alert history, newest first.

        On the first call, if a history_path was configured, the JSONL
        file is loaded to restore history from before the last restart.

        Args:
            limit: Maximum number of alerts to return (default: all)

        Returns:
            List of recent alerts, newest first
        """
        with self._lock:
            if not self._history_loaded:
                self._load_history_from_file()
                self._history_loaded = True

            history = list(self._history)
            history.reverse()

            if limit:
                history = history[:limit]

            return history

    def clear_history(self):
        """Clear in-memory alert history (does not delete the JSONL file)."""
        with self._lock:
            self._history.clear()

    # ------------------------------------------------------------------
    # JSONL persistence (private)
    # ------------------------------------------------------------------

    def _persist_alert(self, alert: Alert):
        """Append alert to JSONL file if persistence is configured."""
        if not self._history_path:
            return
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            with self._history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict()) + "\n")
        except Exception:
            pass  # Never crash the alert pipeline due to persistence failure

    def _load_history_from_file(self):
        """Load JSONL history file into the in-memory deque."""
        if not self._history_path or not self._history_path.exists():
            return
        try:
            rows = []
            with self._history_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

            # Load the most recent max_history entries
            for row in rows[-self._history.maxlen:]:  # type: ignore[arg-type]
                try:
                    alert = self._row_to_alert(row)
                    if alert:
                        self._history.append(alert)
                except Exception:
                    continue
        except Exception:
            pass

    @staticmethod
    def _row_to_alert(row: dict) -> Alert | None:
        """Reconstruct an Alert from a JSONL row dict."""
        try:
            return Alert(
                id=row["id"],
                rule_id=row.get("rule_id", ""),
                timestamp=datetime.fromisoformat(row["timestamp"]),
                trigger=AlertTrigger(row["trigger"]),
                severity=AlertSeverity(row["severity"]),
                title=row.get("title", ""),
                message=row.get("message", ""),
                context=row.get("context", {}),
                channels=[ChannelType(ch) for ch in row.get("channels", [])],
                delivered=datetime.fromisoformat(row["delivered"]) if row.get("delivered") else None,
                delivery_attempts=row.get("delivery_attempts", 0),
                delivery_errors=row.get("delivery_errors", []),
            )
        except Exception:
            return None

    def set_history_path(self, path: Path):
        """Set or update the JSONL persistence path at runtime."""
        with self._lock:
            self._history_path = path
            self._history_loaded = False  # force reload on next get_history


# Global alert manager instance
_manager = AlertManager()


def get_manager() -> AlertManager:
    """Get the global alert manager instance."""
    return _manager
