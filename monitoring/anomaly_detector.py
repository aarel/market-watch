"""
Anomaly detection for agent event stream.

Monitors warn/fail event rates and detects unusual spikes that indicate
system degradation or issues requiring attention.
"""
from collections import deque
from datetime import UTC, datetime, timedelta
from threading import RLock


class AnomalyDetector:
    """
    Detects anomalies in agent event stream.

    Uses sliding window to track recent event rates and identifies spikes
    in warn/fail counts that exceed normal thresholds.
    """

    def __init__(
        self,
        window_minutes: int = 60,
        spike_threshold: float = 3.0,
        min_events_for_detection: int = 10
    ):
        """
        Initialize anomaly detector.

        Args:
            window_minutes: Time window for rate calculation (default 60 min)
            spike_threshold: Multiple of baseline rate to trigger anomaly (default 3x)
            min_events_for_detection: Minimum events needed before detecting anomalies
        """
        self.window_minutes = window_minutes
        self.spike_threshold = spike_threshold
        self.min_events_for_detection = min_events_for_detection

        # Store recent events with timestamps
        self._warn_events: deque = deque()
        self._fail_events: deque = deque()
        self._lock = RLock()

        # Baseline rates (events per minute)
        self._baseline_warn_rate: float | None = None
        self._baseline_fail_rate: float | None = None

    def record_event(self, outcome: str, timestamp: datetime | None = None):
        """
        Record an event occurrence.

        Args:
            outcome: Event outcome ("ok", "warn", or "fail")
            timestamp: Event timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC)
        timestamp = self._normalize_timestamp(timestamp)

        with self._lock:
            if outcome == "warn":
                self._warn_events.append(timestamp)
            elif outcome == "fail":
                self._fail_events.append(timestamp)

            # Clean old events outside window
            self._clean_old_events()

    def _clean_old_events(self):
        """Remove events outside the time window."""
        cutoff = datetime.now(UTC) - timedelta(minutes=self.window_minutes)

        while self._warn_events and self._warn_events[0] < cutoff:
            self._warn_events.popleft()

        while self._fail_events and self._fail_events[0] < cutoff:
            self._fail_events.popleft()

    def _calculate_rate(self, events: deque) -> float:
        """
        Calculate events per minute rate.

        Args:
            events: Deque of event timestamps

        Returns:
            Events per minute rate
        """
        if not events:
            return 0.0

        # Calculate time span of events
        if len(events) < 2:
            return 0.0

        time_span = abs((events[-1] - events[0]).total_seconds()) / 60.0
        if time_span == 0:
            return 0.0

        return len(events) / time_span

    @staticmethod
    def _normalize_timestamp(timestamp: datetime) -> datetime:
        """Normalize timestamps to timezone-aware UTC."""
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC)

    def update_baseline(self):
        """
        Update baseline rates based on current window.

        Should be called periodically during normal operation to establish
        what "normal" event rates look like.
        """
        with self._lock:
            self._clean_old_events()

            if len(self._warn_events) >= self.min_events_for_detection:
                self._baseline_warn_rate = self._calculate_rate(self._warn_events)

            if len(self._fail_events) >= self.min_events_for_detection:
                self._baseline_fail_rate = self._calculate_rate(self._fail_events)

    def detect_anomaly(self) -> dict[str, any] | None:
        """
        Check for anomalies in recent event rates.

        Returns:
            Anomaly details if detected, None otherwise.
            Dictionary contains: type, current_rate, baseline_rate, severity, message
        """
        with self._lock:
            self._clean_old_events()

            # Need baseline before we can detect anomalies
            if self._baseline_warn_rate is None and self._baseline_fail_rate is None:
                return None

            # Calculate current rates
            current_warn_rate = self._calculate_rate(self._warn_events)
            current_fail_rate = self._calculate_rate(self._fail_events)

            # Check for warn rate spike
            if self._baseline_warn_rate and self._baseline_warn_rate > 0:
                warn_multiplier = current_warn_rate / self._baseline_warn_rate
                if warn_multiplier >= self.spike_threshold and len(self._warn_events) >= self.min_events_for_detection:
                    return {
                        "type": "warn_spike",
                        "current_rate": round(current_warn_rate, 2),
                        "baseline_rate": round(self._baseline_warn_rate, 2),
                        "multiplier": round(warn_multiplier, 2),
                        "severity": "medium",
                        "message": f"Warning event rate is {warn_multiplier:.1f}x baseline ({current_warn_rate:.1f}/min vs {self._baseline_warn_rate:.1f}/min)",
                        "event_count": len(self._warn_events),
                    }

            # Check for fail rate spike (more severe)
            if self._baseline_fail_rate and self._baseline_fail_rate > 0:
                fail_multiplier = current_fail_rate / self._baseline_fail_rate
                if fail_multiplier >= self.spike_threshold and len(self._fail_events) >= self.min_events_for_detection:
                    return {
                        "type": "fail_spike",
                        "current_rate": round(current_fail_rate, 2),
                        "baseline_rate": round(self._baseline_fail_rate, 2),
                        "multiplier": round(fail_multiplier, 2),
                        "severity": "high",
                        "message": f"Failure event rate is {fail_multiplier:.1f}x baseline ({current_fail_rate:.1f}/min vs {self._baseline_fail_rate:.1f}/min)",
                        "event_count": len(self._fail_events),
                    }

            return None

    def get_status(self) -> dict[str, any]:
        """
        Get current detector status.

        Returns:
            Dictionary with current rates, baselines, and event counts
        """
        with self._lock:
            self._clean_old_events()

            current_warn_rate = self._calculate_rate(self._warn_events)
            current_fail_rate = self._calculate_rate(self._fail_events)

            return {
                "window_minutes": self.window_minutes,
                "warn_events": {
                    "count": len(self._warn_events),
                    "rate_per_min": round(current_warn_rate, 2),
                    "baseline_rate": round(self._baseline_warn_rate, 2) if self._baseline_warn_rate else None,
                },
                "fail_events": {
                    "count": len(self._fail_events),
                    "rate_per_min": round(current_fail_rate, 2),
                    "baseline_rate": round(self._baseline_fail_rate, 2) if self._baseline_fail_rate else None,
                },
                "anomaly_detected": self.detect_anomaly() is not None,
            }

    def reset(self):
        """Clear all events and baselines (useful for testing)."""
        with self._lock:
            self._warn_events.clear()
            self._fail_events.clear()
            self._baseline_warn_rate = None
            self._baseline_fail_rate = None


# Global detector instance
_detector = AnomalyDetector()


def get_detector() -> AnomalyDetector:
    """Get the global anomaly detector instance."""
    return _detector
