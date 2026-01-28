"""
Backtesting engine for Market-Watch trading strategies.

This module provides historical data management, strategy simulation,
and performance analytics for validating trading strategies before
deploying them with real capital.

Example usage:
    from backtest import BacktestEngine, HistoricalData

    # Load historical data
    data = HistoricalData()
    data.download(['AAPL', 'GOOGL'], start='2021-01-01', end='2023-12-31')

    # Run backtest
    engine = BacktestEngine(
        data=data,
        initial_capital=100000
    )
    results = engine.run(symbols=['AAPL', 'GOOGL'])

    # View results
    print(results.summary())
    results.to_csv('backtest_results.csv')
"""

from backtest.data import HistoricalData
from backtest.engine import BacktestEngine
from backtest.metrics import calculate_metrics
from backtest.results import BacktestResults

__all__ = [
    'HistoricalData',
    'BacktestEngine',
    'BacktestResults',
    'calculate_metrics',
]
