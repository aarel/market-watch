"""Tests for latency tracking system."""
import unittest

from server.latency_tracker import LatencyTracker


class TestLatencyTracker(unittest.TestCase):
    """Test latency tracker functionality."""

    def setUp(self):
        """Create fresh tracker for each test."""
        self.tracker = LatencyTracker(window_size=100)

    def test_records_single_measurement(self):
        """Test that tracker records a single measurement."""
        self.tracker.record("/api/health", 10.5)
        p50, p95, count = self.tracker.get_percentiles("/api/health")

        self.assertEqual(count, 1)
        self.assertEqual(p50, 10.5)
        self.assertEqual(p95, 10.5)

    def test_calculates_percentiles_correctly(self):
        """Test percentile calculations with multiple measurements."""
        # Record measurements: 1, 2, 3, ..., 100
        for i in range(1, 101):
            self.tracker.record("/api/test", float(i))

        p50, p95, count = self.tracker.get_percentiles("/api/test")

        self.assertEqual(count, 100)
        # p50 should be around 50, p95 around 95
        self.assertGreater(p50, 45)
        self.assertLess(p50, 55)
        self.assertGreater(p95, 90)
        self.assertLess(p95, 100)

    def test_tracks_multiple_endpoints(self):
        """Test that tracker maintains separate measurements per endpoint."""
        self.tracker.record("/api/health", 5.0)
        self.tracker.record("/api/status", 10.0)
        self.tracker.record("/api/health", 7.0)

        health_p50, health_p95, health_count = self.tracker.get_percentiles("/api/health")
        status_p50, status_p95, status_count = self.tracker.get_percentiles("/api/status")

        self.assertEqual(health_count, 2)
        self.assertEqual(status_count, 1)
        self.assertIn(health_p50, [5.0, 7.0])  # p50 of [5, 7] is 7.0 (index 1)
        self.assertEqual(status_p50, 10.0)

    def test_respects_window_size(self):
        """Test that tracker maintains rolling window and drops old measurements."""
        tracker = LatencyTracker(window_size=10)

        # Record 20 measurements
        for i in range(20):
            tracker.record("/api/test", float(i))

        p50, p95, count = tracker.get_percentiles("/api/test")

        # Should only keep last 10 measurements (10-19)
        self.assertEqual(count, 10)
        self.assertGreater(p50, 13)  # Should be around 14-15 (middle of 10-19)

    def test_returns_zero_for_unknown_endpoint(self):
        """Test that tracker returns zeros for endpoints with no measurements."""
        p50, p95, count = self.tracker.get_percentiles("/api/unknown")

        self.assertEqual(count, 0)
        self.assertEqual(p50, 0.0)
        self.assertEqual(p95, 0.0)

    def test_get_all_percentiles(self):
        """Test retrieving percentiles for all tracked endpoints."""
        self.tracker.record("/api/health", 5.0)
        self.tracker.record("/api/health", 10.0)
        self.tracker.record("/api/status", 15.0)

        all_percentiles = self.tracker.get_all_percentiles()

        self.assertIn("/api/health", all_percentiles)
        self.assertIn("/api/status", all_percentiles)

        health = all_percentiles["/api/health"]
        self.assertEqual(health["samples"], 2)
        self.assertGreater(health["p50_ms"], 0)

        status = all_percentiles["/api/status"]
        self.assertEqual(status["samples"], 1)
        self.assertEqual(status["p50_ms"], 15.0)

    def test_get_summary(self):
        """Test aggregate summary across all endpoints."""
        self.tracker.record("/api/health", 5.0)
        self.tracker.record("/api/health", 10.0)
        self.tracker.record("/api/status", 15.0)
        self.tracker.record("/api/status", 20.0)

        summary = self.tracker.get_summary()

        self.assertEqual(summary["samples"], 4)
        # Summary should aggregate all measurements
        self.assertGreater(summary["p50_ms"], 0)
        self.assertGreater(summary["p95_ms"], summary["p50_ms"])

    def test_summary_returns_zero_when_empty(self):
        """Test that summary returns zeros when no measurements exist."""
        summary = self.tracker.get_summary()

        self.assertEqual(summary["samples"], 0)
        self.assertEqual(summary["p50_ms"], 0.0)
        self.assertEqual(summary["p95_ms"], 0.0)

    def test_reset_clears_all_measurements(self):
        """Test that reset clears all tracked measurements."""
        self.tracker.record("/api/health", 5.0)
        self.tracker.record("/api/status", 10.0)

        self.tracker.reset()

        summary = self.tracker.get_summary()
        self.assertEqual(summary["samples"], 0)

        all_percentiles = self.tracker.get_all_percentiles()
        self.assertEqual(len(all_percentiles), 0)

    def test_thread_safety_concurrent_records(self):
        """Test that tracker handles concurrent recordings safely."""
        import threading

        def record_many():
            for i in range(100):
                self.tracker.record("/api/test", float(i))

        threads = [threading.Thread(target=record_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have recorded something (exact count depends on window size)
        p50, p95, count = self.tracker.get_percentiles("/api/test")
        self.assertGreater(count, 0)
        self.assertLessEqual(count, 100)  # Window size limit

    def test_percentile_precision(self):
        """Test that percentiles are rounded to 2 decimal places."""
        self.tracker.record("/api/test", 1.23456)
        self.tracker.record("/api/test", 2.34567)

        p50, p95, count = self.tracker.get_percentiles("/api/test")

        # Check that values are rounded
        self.assertEqual(len(str(p50).split('.')[-1]), 2)  # 2 decimal places

    def test_handles_large_values(self):
        """Test that tracker handles large latency values correctly."""
        self.tracker.record("/api/slow", 1000.0)
        self.tracker.record("/api/slow", 2000.0)
        self.tracker.record("/api/slow", 5000.0)

        p50, p95, count = self.tracker.get_percentiles("/api/slow")

        self.assertEqual(count, 3)
        self.assertEqual(p50, 2000.0)
        self.assertEqual(p95, 5000.0)


if __name__ == "__main__":
    unittest.main()
