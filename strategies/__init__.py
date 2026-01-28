"""
Trading strategies package.

This package contains all available trading strategies. Strategies
can be selected and configured dynamically at runtime.

Available strategies:
- MomentumStrategy: Buys on strong momentum, sells on reversal
- MeanReversionStrategy: Buys when price deviates below MA, sells on return
- BreakoutStrategy: Buys on high breakout, sells on low breakdown
- RSIStrategy: Buys when oversold (RSI < 30), sells when overbought (RSI > 70)

Usage:
    from strategies import MomentumStrategy, get_strategy

    # Direct instantiation
    strategy = MomentumStrategy(lookback_days=20, momentum_threshold=0.02)
    signal = strategy.analyze(symbol, bars, current_price, position)

    # Via registry
    strategy = get_strategy('mean_reversion', ma_period=20, deviation_threshold=0.03)
"""

from strategies.base import Strategy, TradingSignal, SignalType
from strategies.momentum import MomentumStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.breakout import BreakoutStrategy
from strategies.rsi import RSIStrategy

# Registry of all available strategies
AVAILABLE_STRATEGIES = {
    'momentum': MomentumStrategy,
    'mean_reversion': MeanReversionStrategy,
    'breakout': BreakoutStrategy,
    'rsi': RSIStrategy,
}


def get_strategy(name: str, **params) -> Strategy:
    """
    Get a strategy instance by name.

    Args:
        name: Strategy name ('momentum', 'mean_reversion', etc.)
        **params: Strategy-specific parameters

    Returns:
        Strategy instance

    Raises:
        ValueError: If strategy name is unknown

    Example:
        strategy = get_strategy('momentum', lookback_days=30)
    """
    name = name.lower()
    if name not in AVAILABLE_STRATEGIES:
        available = ', '.join(AVAILABLE_STRATEGIES.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

    strategy_class = AVAILABLE_STRATEGIES[name]
    return strategy_class(**params)


def list_strategies() -> list[str]:
    """
    List all available strategy names.

    Returns:
        List of strategy names
    """
    return list(AVAILABLE_STRATEGIES.keys())


__all__ = [
    'Strategy',
    'TradingSignal',
    'SignalType',
    'MomentumStrategy',
    'MeanReversionStrategy',
    'BreakoutStrategy',
    'RSIStrategy',
    'get_strategy',
    'list_strategies',
    'AVAILABLE_STRATEGIES',
]
