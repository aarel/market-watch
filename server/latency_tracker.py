"""
Latency tracking for API endpoints.

Tracks request duration and calculates percentiles (p50, p95) for monitoring.
Uses rolling window to maintain recent measurements without unbounded memory growth.
"""
import time
from collections import defaultdict, deque
from typing import Dict, List, Tuple
from threading import Lock
import statistics


class LatencyTracker:
    """Thread-safe latency tracker with rolling window."""

    def __init__(self, window_size: int = 1000):
        """
        Initialize latency tracker.

        Args:
            window_size: Maximum number of measurements to keep per endpoint
        """
        self.window_size = window_size
        self._measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._lock = Lock()

    def record(self, endpoint: str, duration_ms: float):
        """
        Record a request duration.

        Args:
            endpoint: API endpoint path (e.g., "/api/health")
            duration_ms: Request duration in milliseconds
        """
        with self._lock:
            self._measurements[endpoint].append(duration_ms)

    def get_percentiles(self, endpoint: str) -> Tuple[float, float, int]:
        """
        Get p50 and p95 latency for an endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Tuple of (p50_ms, p95_ms, sample_count)
        """
        with self._lock:
            measurements = list(self._measurements.get(endpoint, []))

        if not measurements:
            return (0.0, 0.0, 0)

        count = len(measurements)
        sorted_measurements = sorted(measurements)

        # Calculate percentiles
        p50_idx = int(count * 0.50)
        p95_idx = int(count * 0.95)

        p50 = sorted_measurements[p50_idx] if p50_idx < count else sorted_measurements[-1]
        p95 = sorted_measurements[p95_idx] if p95_idx < count else sorted_measurements[-1]

        return (round(p50, 2), round(p95, 2), count)

    def get_all_percentiles(self) -> Dict[str, Dict[str, float]]:
        """
        Get latency percentiles for all tracked endpoints.

        Returns:
            Dictionary mapping endpoint -> {p50, p95, count}
        """
        with self._lock:
            endpoints = list(self._measurements.keys())

        result = {}
        for endpoint in endpoints:
            p50, p95, count = self.get_percentiles(endpoint)
            result[endpoint] = {
                "p50_ms": p50,
                "p95_ms": p95,
                "samples": count
            }

        return result

    def get_summary(self) -> Dict[str, float]:
        """
        Get aggregate latency summary across all endpoints.

        Returns:
            Dictionary with overall p50, p95, and total sample count
        """
        with self._lock:
            all_measurements = []
            for measurements in self._measurements.values():
                all_measurements.extend(measurements)

        if not all_measurements:
            return {"p50_ms": 0.0, "p95_ms": 0.0, "samples": 0}

        sorted_all = sorted(all_measurements)
        count = len(sorted_all)

        p50_idx = int(count * 0.50)
        p95_idx = int(count * 0.95)

        p50 = sorted_all[p50_idx] if p50_idx < count else sorted_all[-1]
        p95 = sorted_all[p95_idx] if p95_idx < count else sorted_all[-1]

        return {
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "samples": count
        }

    def reset(self):
        """Clear all measurements (useful for testing)."""
        with self._lock:
            self._measurements.clear()


# Global tracker instance
_tracker = LatencyTracker(window_size=1000)


def get_tracker() -> LatencyTracker:
    """Get the global latency tracker instance."""
    return _tracker
