"""
Momentum trading strategy.

Buys stocks showing strong upward price momentum and sells when
momentum reverses or stop-loss is triggered.
"""

import pandas as pd
from typing import Optional

from strategies.base import Strategy, TradingSignal, SignalType
import config


class MomentumStrategy(Strategy):
    """
    Momentum/trend following strategy.

    **Logic:**
    - Calculate momentum as rate of change over lookback period
    - Buy when momentum exceeds threshold
    - Sell when momentum reverses below sell threshold
    - Apply stop-loss for risk management

    **Parameters:**
    - lookback_days: Number of days for momentum calculation (default: 20)
    - momentum_threshold: Minimum momentum to trigger buy (default: 0.02 = 2%)
    - sell_threshold: Momentum threshold to trigger sell (default: -0.01 = -1%)
    - stop_loss_pct: Maximum loss before automatic exit (default: 0.05 = 5%)
    """

    def __init__(
        self,
        lookback_days: int = None,
        momentum_threshold: float = None,
        sell_threshold: float = None,
        stop_loss_pct: float = None
    ):
        """
        Initialize momentum strategy.

        Args:
            lookback_days: Period for momentum calculation (default from config)
            momentum_threshold: Buy signal threshold (default from config)
            sell_threshold: Sell signal threshold (default from config)
            stop_loss_pct: Stop loss percentage (default from config)
        """
        self.lookback_days = lookback_days or config.LOOKBACK_DAYS
        self.momentum_threshold = momentum_threshold or config.MOMENTUM_THRESHOLD
        self.sell_threshold = sell_threshold or config.SELL_THRESHOLD
        self.stop_loss_pct = stop_loss_pct or config.STOP_LOSS_PCT

    @property
    def name(self) -> str:
        return "Momentum Strategy"

    @property
    def description(self) -> str:
        return f"Buys stocks with >{self.momentum_threshold:.1%} momentum, sells on reversal or {self.stop_loss_pct:.1%} stop-loss"

    @property
    def required_history(self) -> int:
        return self.lookback_days

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: float,
        current_position: Optional[dict] = None
    ) -> TradingSignal:
        """
        Analyze symbol and generate trading signal.

        Args:
            symbol: Ticker symbol
            bars: Historical OHLCV data
            current_price: Current market price
            current_position: Current position info or None

        Returns:
            TradingSignal
        """
        # Calculate momentum
        momentum = self._calculate_momentum(bars)

        has_position = current_position is not None

        if has_position:
            return self._analyze_with_position(
                symbol, current_price, momentum, current_position
            )
        else:
            return self._analyze_without_position(
                symbol, current_price, momentum
            )

    def _calculate_momentum(self, bars: pd.DataFrame) -> float:
        """
        Calculate momentum as rate of change over lookback period.

        Args:
            bars: Historical OHLCV data

        Returns:
            Momentum value (e.g., 0.05 = 5% gain over period)
        """
        if len(bars) < 2:
            return 0.0

        current_close = bars['close'].iloc[-1]
        past_close = bars['close'].iloc[0]

        momentum = (current_close - past_close) / past_close
        return float(momentum)

    def _analyze_with_position(
        self,
        symbol: str,
        current_price: float,
        momentum: float,
        position: dict
    ) -> TradingSignal:
        """Generate signal when holding a position."""
        entry_price = position['entry_price']
        unrealized_pnl_pct = position['unrealized_pnl_pct']

        # Stop loss check
        if unrealized_pnl_pct <= -self.stop_loss_pct:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=1.0,  # High urgency
                reason=f"Stop loss triggered ({unrealized_pnl_pct:.1%} loss)",
                current_price=current_price,
                metadata={
                    'momentum': momentum,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'stop_loss'
                }
            )

        # Momentum reversal check
        if momentum < self.sell_threshold:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=abs(momentum),
                reason=f"Momentum turned negative ({momentum:.1%})",
                current_price=current_price,
                metadata={
                    'momentum': momentum,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'momentum_reversal'
                }
            )

        # Hold position
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=momentum,
            reason=f"Holding (momentum: {momentum:.1%}, P/L: {unrealized_pnl_pct:.1%})",
            current_price=current_price,
            metadata={
                'momentum': momentum,
                'entry_price': entry_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
            }
        )

    def _analyze_without_position(
        self,
        symbol: str,
        current_price: float,
        momentum: float
    ) -> TradingSignal:
        """Generate signal when not holding a position."""
        # Check for buy signal
        if momentum > self.momentum_threshold:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.BUY,
                strength=momentum,
                reason=f"Strong momentum ({momentum:.1%} over {self.lookback_days} days)",
                current_price=current_price,
                metadata={
                    'momentum': momentum,
                    'lookback_days': self.lookback_days,
                }
            )

        # No signal - momentum too weak
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=momentum,
            reason=f"Momentum below threshold ({momentum:.1%} < {self.momentum_threshold:.1%})",
            current_price=current_price,
            metadata={
                'momentum': momentum,
            }
        )

    def get_parameters(self) -> dict:
        """Get current strategy parameters."""
        return {
            'lookback_days': self.lookback_days,
            'momentum_threshold': self.momentum_threshold,
            'sell_threshold': self.sell_threshold,
            'stop_loss_pct': self.stop_loss_pct,
        }
