"""Unit tests for BrokerQueryService caching and query optimization."""
import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from broker_query_service import BrokerQueryService


class TestBrokerQueryService(unittest.TestCase):
    """Test BrokerQueryService caching behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_broker = Mock()
        # Use short TTLs for faster tests
        self.service = BrokerQueryService(
            broker=self.mock_broker,
            account_ttl_seconds=0.1,  # 100ms for testing
            positions_ttl_seconds=0.05,  # 50ms for testing
            market_open_ttl_seconds=0.1,  # 100ms for testing
        )

    def test_get_account_caches_result(self):
        """Test that get_account() caches result and avoids redundant calls."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # First call - cache miss
        result1 = self.service.get_account()
        assert result1 == mock_account
        assert self.mock_broker.get_account.call_count == 1

        # Second call within TTL - cache hit
        result2 = self.service.get_account()
        assert result2 == mock_account
        assert self.mock_broker.get_account.call_count == 1  # No additional call

        # Verify cache stats
        stats = self.service.get_cache_stats()
        assert stats['account']['hits'] == 1
        assert stats['account']['misses'] == 1
        assert stats['account']['hit_rate'] == 50.0

    def test_get_account_expires_after_ttl(self):
        """Test that account cache expires after TTL."""
        mock_account1 = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        mock_account2 = SimpleNamespace(portfolio_value=105000, buying_power=52000)
        self.mock_broker.get_account.side_effect = [mock_account1, mock_account2]

        # First call
        result1 = self.service.get_account()
        assert result1 == mock_account1

        # Force expiration without sleeping to avoid timing flakes
        self.service._account_cache.expires_at = time.time() - 1

        # Second call after TTL - cache miss, fetches new data
        result2 = self.service.get_account()
        assert result2 == mock_account2
        assert self.mock_broker.get_account.call_count == 2

    def test_get_positions_caches_result(self):
        """Test that get_positions() caches result."""
        mock_positions = [
            SimpleNamespace(symbol="AAPL", qty=10, market_value=1500),
            SimpleNamespace(symbol="GOOGL", qty=5, market_value=2000),
        ]
        self.mock_broker.get_positions.return_value = mock_positions

        # First call - cache miss
        result1 = self.service.get_positions()
        assert result1 == mock_positions
        assert self.mock_broker.get_positions.call_count == 1

        # Second call within TTL - cache hit
        result2 = self.service.get_positions()
        assert result2 == mock_positions
        assert self.mock_broker.get_positions.call_count == 1

    def test_get_position_uses_cached_positions(self):
        """Test that get_position() uses cached positions list when available."""
        mock_positions = [
            SimpleNamespace(symbol="AAPL", qty=10),
            SimpleNamespace(symbol="GOOGL", qty=5),
        ]
        self.mock_broker.get_positions.return_value = mock_positions

        # Populate cache
        self.service.get_positions()

        # get_position should use cache, not call broker
        result = self.service.get_position("AAPL")
        assert result.symbol == "AAPL"
        assert result.qty == 10
        assert self.mock_broker.get_position.call_count == 0  # Not called

    def test_get_position_fetches_directly_on_cache_miss(self):
        """Test that get_position() fetches directly when cache expired."""
        mock_position = SimpleNamespace(symbol="AAPL", qty=10)
        self.mock_broker.get_position.return_value = mock_position

        # No positions cache populated - should fetch directly
        result = self.service.get_position("AAPL")
        assert result == mock_position
        assert self.mock_broker.get_position.call_count == 1

    def test_is_market_open_caches_result(self):
        """Test that is_market_open() caches result."""
        self.mock_broker.is_market_open.return_value = True

        # First call - cache miss
        result1 = self.service.is_market_open()
        assert result1 is True
        assert self.mock_broker.is_market_open.call_count == 1

        # Second call within TTL - cache hit
        result2 = self.service.is_market_open()
        assert result2 is True
        assert self.mock_broker.is_market_open.call_count == 1

    def test_get_portfolio_value_uses_account_cache(self):
        """Test that get_portfolio_value() consolidates through account cache."""
        mock_account = SimpleNamespace(portfolio_value=100000.50, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # First call
        portfolio_value = self.service.get_portfolio_value()
        assert portfolio_value == 100000.50
        assert self.mock_broker.get_account.call_count == 1

        # Second call uses cache
        portfolio_value2 = self.service.get_portfolio_value()
        assert portfolio_value2 == 100000.50
        assert self.mock_broker.get_account.call_count == 1  # Still 1

    def test_get_buying_power_uses_account_cache(self):
        """Test that get_buying_power() consolidates through account cache."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000.75)
        self.mock_broker.get_account.return_value = mock_account

        # First call
        buying_power = self.service.get_buying_power()
        assert buying_power == 50000.75
        assert self.mock_broker.get_account.call_count == 1

        # Second call uses cache
        buying_power2 = self.service.get_buying_power()
        assert buying_power2 == 50000.75
        assert self.mock_broker.get_account.call_count == 1

    def test_portfolio_value_and_buying_power_share_cache(self):
        """Test that portfolio_value and buying_power share same account cache."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # Call both methods
        portfolio_value = self.service.get_portfolio_value()
        buying_power = self.service.get_buying_power()

        assert portfolio_value == 100000
        assert buying_power == 50000
        # Only ONE get_account() call should have been made
        assert self.mock_broker.get_account.call_count == 1

    def test_submit_order_invalidates_caches(self):
        """Test that submit_order() invalidates account and positions caches."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        mock_positions = [SimpleNamespace(symbol="AAPL", qty=10)]
        self.mock_broker.get_account.return_value = mock_account
        self.mock_broker.get_positions.return_value = mock_positions

        # Populate caches
        self.service.get_account()
        self.service.get_positions()
        assert self.mock_broker.get_account.call_count == 1
        assert self.mock_broker.get_positions.call_count == 1

        # Submit order - should invalidate caches
        self.service.submit_order(symbol="AAPL", qty=5, side="buy")

        # Next calls should fetch fresh data
        self.service.get_account()
        self.service.get_positions()
        assert self.mock_broker.get_account.call_count == 2
        assert self.mock_broker.get_positions.call_count == 2

    def test_clear_cache_clears_all_caches(self):
        """Test that clear_cache() clears all cached data."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account
        self.mock_broker.is_market_open.return_value = True

        # Populate caches
        self.service.get_account()
        self.service.is_market_open()
        assert self.mock_broker.get_account.call_count == 1
        assert self.mock_broker.is_market_open.call_count == 1

        # Clear cache
        self.service.clear_cache()

        # Next calls should fetch fresh data
        self.service.get_account()
        self.service.is_market_open()
        assert self.mock_broker.get_account.call_count == 2
        assert self.mock_broker.is_market_open.call_count == 2

    def test_cache_stats_tracking(self):
        """Test that cache statistics are tracked correctly."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # 1 miss, 3 hits
        self.service.get_account()  # miss
        self.service.get_account()  # hit
        self.service.get_account()  # hit
        self.service.get_account()  # hit

        stats = self.service.get_cache_stats()
        assert stats['account']['misses'] == 1
        assert stats['account']['hits'] == 3
        assert stats['account']['hit_rate'] == 75.0

    def test_passthrough_methods_not_cached(self):
        """Test that passthrough methods call broker directly every time."""
        self.mock_broker.get_current_price.return_value = 150.50
        self.mock_broker.get_bars.return_value = []

        # Multiple calls should each hit broker
        self.service.get_current_price("AAPL")
        self.service.get_current_price("AAPL")
        assert self.mock_broker.get_current_price.call_count == 2

        self.service.get_bars("AAPL", days=30)
        self.service.get_bars("AAPL", days=30)
        assert self.mock_broker.get_bars.call_count == 2

    def test_async_wrapper_get_account(self):
        """Test async wrapper for get_account()."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # Run async method
        result = asyncio.run(self.service.get_account_async())
        assert result == mock_account
        assert self.mock_broker.get_account.call_count == 1

    def test_async_wrapper_is_market_open(self):
        """Test async wrapper for is_market_open()."""
        self.mock_broker.is_market_open.return_value = True

        # Run async method
        result = asyncio.run(self.service.is_market_open_async())
        assert result is True
        assert self.mock_broker.is_market_open.call_count == 1

    def test_thread_safety_concurrent_access(self):
        """Test that cache operations are thread-safe."""
        mock_account = SimpleNamespace(portfolio_value=100000, buying_power=50000)
        self.mock_broker.get_account.return_value = mock_account

        # Simulate concurrent access from multiple threads
        import threading
        results = []

        def access_cache():
            for _ in range(10):
                account = self.service.get_account()
                results.append(account)

        threads = [threading.Thread(target=access_cache) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should return same cached account
        assert all(r == mock_account for r in results)
        # Should only call broker once (or very few times due to race)
        assert self.mock_broker.get_account.call_count <= 5


if __name__ == '__main__':
    unittest.main()
