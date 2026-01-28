"""Tests for broker universe enforcement."""
import unittest
from unittest.mock import patch, MagicMock

from broker import AlpacaBroker
from fake_broker import FakeBroker
from universe import Universe


class TestBrokerUniverseEnforcement(unittest.TestCase):
    """Test that brokers enforce universe constraints."""

    def test_fake_broker_defaults_to_simulation(self):
        """FakeBroker defaults to SIMULATION universe if not specified."""
        broker = FakeBroker()
        self.assertEqual(broker.universe, Universe.SIMULATION)

    def test_fake_broker_accepts_simulation_universe(self):
        """FakeBroker accepts explicit SIMULATION universe."""
        broker = FakeBroker(universe=Universe.SIMULATION)
        self.assertEqual(broker.universe, Universe.SIMULATION)

    def test_fake_broker_rejects_live_universe(self):
        """FakeBroker rejects LIVE universe."""
        with self.assertRaises(ValueError) as ctx:
            FakeBroker(universe=Universe.LIVE)

        self.assertIn("SIMULATION", str(ctx.exception))
        self.assertIn("LIVE", str(ctx.exception))

    def test_fake_broker_rejects_paper_universe(self):
        """FakeBroker rejects PAPER universe."""
        with self.assertRaises(ValueError) as ctx:
            FakeBroker(universe=Universe.PAPER)

        self.assertIn("SIMULATION", str(ctx.exception))
        self.assertIn("PAPER", str(ctx.exception))

    @patch('broker.tradeapi.REST')
    @patch('broker.config.ALPACA_API_KEY', 'test_key')
    @patch('broker.config.ALPACA_SECRET_KEY', 'test_secret')
    @patch('broker.config.get_alpaca_url', return_value='https://test.alpaca.markets')
    @patch('broker.config.DATA_FEED', 'iex')
    def test_alpaca_broker_accepts_live_universe(self, mock_url, mock_rest):
        """AlpacaBroker accepts LIVE universe."""
        # Mock the API to avoid actual connection
        mock_api = MagicMock()
        mock_account = MagicMock()
        mock_account.status = 'ACTIVE'
        mock_account.buying_power = '10000.0'
        mock_account.portfolio_value = '10000.0'
        mock_api.get_account.return_value = mock_account
        mock_rest.return_value = mock_api

        broker = AlpacaBroker(universe=Universe.LIVE)
        self.assertEqual(broker.universe, Universe.LIVE)

    @patch('broker.tradeapi.REST')
    @patch('broker.config.ALPACA_API_KEY', 'test_key')
    @patch('broker.config.ALPACA_SECRET_KEY', 'test_secret')
    @patch('broker.config.get_alpaca_url', return_value='https://test.alpaca.markets')
    @patch('broker.config.DATA_FEED', 'iex')
    def test_alpaca_broker_accepts_paper_universe(self, mock_url, mock_rest):
        """AlpacaBroker accepts PAPER universe."""
        # Mock the API to avoid actual connection
        mock_api = MagicMock()
        mock_account = MagicMock()
        mock_account.status = 'ACTIVE'
        mock_account.buying_power = '10000.0'
        mock_account.portfolio_value = '10000.0'
        mock_api.get_account.return_value = mock_account
        mock_rest.return_value = mock_api

        broker = AlpacaBroker(universe=Universe.PAPER)
        self.assertEqual(broker.universe, Universe.PAPER)

    @patch('broker.tradeapi.REST')
    @patch('broker.config.ALPACA_API_KEY', 'test_key')
    @patch('broker.config.ALPACA_SECRET_KEY', 'test_secret')
    @patch('broker.config.get_alpaca_url', return_value='https://test.alpaca.markets')
    @patch('broker.config.DATA_FEED', 'iex')
    def test_alpaca_broker_rejects_simulation_universe(self, mock_url, mock_rest):
        """AlpacaBroker rejects SIMULATION universe."""
        # Mock the API to avoid actual connection
        mock_api = MagicMock()
        mock_rest.return_value = mock_api

        with self.assertRaises(ValueError) as ctx:
            AlpacaBroker(universe=Universe.SIMULATION)

        self.assertIn("AlpacaBroker", str(ctx.exception))
        self.assertIn("SIMULATION", str(ctx.exception))
        self.assertIn("FakeBroker", str(ctx.exception))

    def test_brokers_have_universe_property(self):
        """Both broker types expose universe property."""
        fake = FakeBroker(universe=Universe.SIMULATION)
        self.assertTrue(hasattr(fake, 'universe'))
        self.assertIsInstance(fake.universe, Universe)


if __name__ == "__main__":
    unittest.main()
