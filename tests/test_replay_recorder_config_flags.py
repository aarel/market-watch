import unittest

import config


class TestReplayRecorderConfig(unittest.TestCase):
    def test_defaults_present(self):
        # Ensure new flags exist with types
        self.assertIsNotNone(config.REPLAY_RECORDER_ENABLED)
        self.assertIsInstance(config.REPLAY_RECORDER_ENABLED, bool)
        self.assertGreaterEqual(config.REPLAY_RECORDER_INTERVAL_MINUTES, 1)
        self.assertIsInstance(config.REPLAY_RECORDER_SYMBOLS, list)
        self.assertTrue(config.REPLAY_RECORDER_DIR)


if __name__ == "__main__":
    unittest.main()
