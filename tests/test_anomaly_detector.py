"""Tests for anomaly detection system."""
import unittest
from datetime import datetime, timedelta
from monitoring.anomaly_detector import AnomalyDetector


class TestAnomalyDetector(unittest.TestCase):
    """Test anomaly detector functionality."""

    def setUp(self):
        """Create fresh detector for each test."""
        self.detector = AnomalyDetector(
            window_minutes=60,
            spike_threshold=3.0,
            min_events_for_detection=10
        )

    def test_records_warn_events(self):
        """Test that detector records warn events."""
        self.detector.record_event("warn")
        status = self.detector.get_status()

        self.assertEqual(status["warn_events"]["count"], 1)

    def test_records_fail_events(self):
        """Test that detector records fail events."""
        self.detector.record_event("fail")
        status = self.detector.get_status()

        self.assertEqual(status["fail_events"]["count"], 1)

    def test_ignores_ok_events(self):
        """Test that detector ignores OK events (only tracks warn/fail)."""
        self.detector.record_event("ok")
        status = self.detector.get_status()

        self.assertEqual(status["warn_events"]["count"], 0)
        self.assertEqual(status["fail_events"]["count"], 0)

    def test_cleans_old_events(self):
        """Test that events outside window are removed."""
        # Record old event
        old_time = datetime.now() - timedelta(minutes=90)
        self.detector.record_event("warn", timestamp=old_time)

        # Record recent event
        self.detector.record_event("warn")

        status = self.detector.get_status()
        # Should only have 1 event (recent one)
        self.assertEqual(status["warn_events"]["count"], 1)

    def test_calculates_event_rate(self):
        """Test event rate calculation."""
        now = datetime.now()
        # Record events over 10 minutes (should be ~1 event/min)
        for i in range(10):
            timestamp = now - timedelta(minutes=i)
            self.detector.record_event("warn", timestamp=timestamp)

        status = self.detector.get_status()
        rate = status["warn_events"]["rate_per_min"]

        # Rate should be around 1.0 events per minute
        self.assertGreater(rate, 0.8)
        self.assertLess(rate, 1.5)

    def test_update_baseline(self):
        """Test baseline establishment."""
        # Record 15 events to meet minimum threshold
        now = datetime.now()
        for i in range(15):
            timestamp = now - timedelta(minutes=i)
            self.detector.record_event("warn", timestamp=timestamp)

        self.detector.update_baseline()
        status = self.detector.get_status()

        # Baseline should be set
        self.assertIsNotNone(status["warn_events"]["baseline_rate"])
        self.assertGreater(status["warn_events"]["baseline_rate"], 0)

    def test_no_baseline_without_enough_events(self):
        """Test that baseline isn't set with too few events."""
        # Record only 5 events (below min_events_for_detection=10)
        for i in range(5):
            self.detector.record_event("warn")

        self.detector.update_baseline()
        status = self.detector.get_status()

        # Baseline should still be None
        self.assertIsNone(status["warn_events"]["baseline_rate"])

    def test_detects_warn_spike_anomaly(self):
        """Test detection of warn event spike."""
        now = datetime.now()

        # Establish baseline with 10 events over 45 minutes (~0.22/min)
        for i in range(10):
            timestamp = now - timedelta(minutes=50 - i*5)
            self.detector.record_event("warn", timestamp=timestamp)

        self.detector.update_baseline()

        # Simulate spike: 50 events in last 5 minutes to create clear anomaly
        for i in range(50):
            timestamp = now - timedelta(seconds=i*6)  # Spread over ~5 minutes
            self.detector.record_event("warn", timestamp=timestamp)

        anomaly = self.detector.detect_anomaly()

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["type"], "warn_spike")
        self.assertEqual(anomaly["severity"], "medium")
        self.assertGreater(anomaly["multiplier"], 3.0)

    def test_detects_fail_spike_anomaly(self):
        """Test detection of fail event spike with high severity."""
        now = datetime.now()

        # Establish baseline with events within the window
        for i in range(10):
            timestamp = now - timedelta(minutes=50 - i*5)
            self.detector.record_event("fail", timestamp=timestamp)

        self.detector.update_baseline()

        # Simulate spike with 50 events
        for i in range(50):
            timestamp = now - timedelta(seconds=i*6)
            self.detector.record_event("fail", timestamp=timestamp)

        anomaly = self.detector.detect_anomaly()

        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly["type"], "fail_spike")
        self.assertEqual(anomaly["severity"], "high")

    def test_no_anomaly_without_baseline(self):
        """Test that no anomaly is detected without baseline."""
        # Record lots of events but don't set baseline
        for i in range(50):
            self.detector.record_event("warn")

        anomaly = self.detector.detect_anomaly()

        # Should return None (no baseline to compare against)
        self.assertIsNone(anomaly)

    def test_no_anomaly_when_rate_below_threshold(self):
        """Test that normal rates don't trigger anomaly."""
        now = datetime.now()

        # Establish baseline with events within the window
        for i in range(15):
            timestamp = now - timedelta(minutes=50 - i*3)
            self.detector.record_event("warn", timestamp=timestamp)

        self.detector.update_baseline()

        # Add a few more events (not enough to spike)
        for i in range(5):
            self.detector.record_event("warn")

        anomaly = self.detector.detect_anomaly()

        # Should not detect anomaly (rate increase is < 3x)
        self.assertIsNone(anomaly)

    def test_reset_clears_everything(self):
        """Test that reset clears events and baseline."""
        # Record events and set baseline
        for i in range(20):
            self.detector.record_event("warn")

        self.detector.update_baseline()

        # Reset
        self.detector.reset()

        status = self.detector.get_status()
        self.assertEqual(status["warn_events"]["count"], 0)
        self.assertEqual(status["fail_events"]["count"], 0)
        self.assertIsNone(status["warn_events"]["baseline_rate"])
        self.assertIsNone(status["fail_events"]["baseline_rate"])

    def test_get_status_returns_complete_info(self):
        """Test that get_status returns all expected fields."""
        self.detector.record_event("warn")
        self.detector.record_event("fail")

        status = self.detector.get_status()

        # Check structure
        self.assertIn("window_minutes", status)
        self.assertIn("warn_events", status)
        self.assertIn("fail_events", status)
        self.assertIn("anomaly_detected", status)

        # Check warn_events structure
        self.assertIn("count", status["warn_events"])
        self.assertIn("rate_per_min", status["warn_events"])
        self.assertIn("baseline_rate", status["warn_events"])

        # Check fail_events structure
        self.assertIn("count", status["fail_events"])
        self.assertIn("rate_per_min", status["fail_events"])
        self.assertIn("baseline_rate", status["fail_events"])

    def test_anomaly_detected_flag_in_status(self):
        """Test that anomaly_detected flag is correct."""
        now = datetime.now()

        # Establish baseline with events within the window
        for i in range(10):
            timestamp = now - timedelta(minutes=50 - i*5)
            self.detector.record_event("warn", timestamp=timestamp)

        self.detector.update_baseline()

        # No spike yet
        status = self.detector.get_status()
        self.assertFalse(status["anomaly_detected"])

        # Create spike with 50 events
        for i in range(50):
            timestamp = now - timedelta(seconds=i*6)
            self.detector.record_event("warn", timestamp=timestamp)

        status = self.detector.get_status()
        self.assertTrue(status["anomaly_detected"])

    def test_custom_spike_threshold(self):
        """Test that custom spike threshold is respected."""
        detector = AnomalyDetector(spike_threshold=5.0, min_events_for_detection=10)
        now = datetime.now()

        # Establish baseline
        for i in range(10):
            timestamp = now - timedelta(hours=2, minutes=i)
            detector.record_event("warn", timestamp=timestamp)

        detector.update_baseline()

        # Create 4x spike (should NOT trigger with threshold=5.0)
        for i in range(15):
            timestamp = now - timedelta(minutes=i % 5)
            detector.record_event("warn", timestamp=timestamp)

        anomaly = detector.detect_anomaly()

        # Should not detect anomaly (multiplier < 5.0)
        self.assertIsNone(anomaly)


if __name__ == "__main__":
    unittest.main()
