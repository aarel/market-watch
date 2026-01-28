"""
Breakout trading strategy.

Buys when price breaks above recent highs and sells when price
breaks below recent lows.
"""

import pandas as pd
from typing import Optional

from strategies.base import Strategy, TradingSignal, SignalType
import config


class BreakoutStrategy(Strategy):
    """
    Breakout strategy based on N-day high/low channels.

    **Logic:**
    - Track highest high and lowest low over lookback period
    - Buy when price breaks above the high (upside breakout)
    - Sell when price breaks below the low (downside breakout)
    - Apply stop-loss for risk management

    **Parameters:**
    - lookback_days: Period for high/low calculation (default: 20)
    - breakout_threshold: % above high to confirm breakout (default: 0.01 = 1%)
    - breakdown_threshold: % below low to confirm breakdown (default: 0.01 = 1%)
    - stop_loss_pct: Maximum loss before automatic exit (default: 0.05 = 5%)
    """

    def __init__(
        self,
        lookback_days: int = 20,
        breakout_threshold: float = 0.01,
        breakdown_threshold: float = 0.01,
        stop_loss_pct: float = None
    ):
        """
        Initialize breakout strategy.

        Args:
            lookback_days: Period for high/low calculation
            breakout_threshold: % above high to trigger buy
            breakdown_threshold: % below low to trigger sell
            stop_loss_pct: Stop loss percentage (default from config)
        """
        self.lookback_days = lookback_days
        self.breakout_threshold = breakout_threshold
        self.breakdown_threshold = breakdown_threshold
        self.stop_loss_pct = stop_loss_pct or config.STOP_LOSS_PCT

    @property
    def name(self) -> str:
        return "Breakout Strategy"

    @property
    def description(self) -> str:
        return f"Buys on {self.lookback_days}-day high breakout, sells on low breakdown"

    @property
    def required_history(self) -> int:
        return self.lookback_days + 5

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: float,
        current_position: Optional[dict] = None
    ) -> TradingSignal:
        """Generate trading signal based on breakouts."""
        # Calculate N-day high and low (excluding current bar)
        recent_bars = bars.iloc[:-1] if len(bars) > 1 else bars
        period_high = recent_bars['high'].rolling(window=self.lookback_days).max().iloc[-1]
        period_low = recent_bars['low'].rolling(window=self.lookback_days).min().iloc[-1]

        # Calculate breakout/breakdown levels
        breakout_level = period_high * (1 + self.breakout_threshold)
        breakdown_level = period_low * (1 - self.breakdown_threshold)

        has_position = current_position is not None

        if has_position:
            return self._analyze_with_position(
                symbol, current_price, period_high, period_low,
                breakout_level, breakdown_level, current_position
            )
        else:
            return self._analyze_without_position(
                symbol, current_price, period_high, period_low,
                breakout_level, breakdown_level
            )

    def _analyze_with_position(
        self,
        symbol: str,
        current_price: float,
        period_high: float,
        period_low: float,
        breakout_level: float,
        breakdown_level: float,
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
                strength=1.0,
                reason=f"Stop loss triggered ({unrealized_pnl_pct:.1%} loss)",
                current_price=current_price,
                metadata={
                    'period_high': period_high,
                    'period_low': period_low,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'stop_loss'
                }
            )

        # Check for breakdown (price breaks below low)
        if current_price < breakdown_level:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=1.0,
                reason=f"Breakdown below {self.lookback_days}-day low (${period_low:.2f})",
                current_price=current_price,
                metadata={
                    'period_high': period_high,
                    'period_low': period_low,
                    'breakdown_level': breakdown_level,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'breakdown'
                }
            )

        # Hold position - riding the trend
        channel_position = (current_price - period_low) / (period_high - period_low) if period_high > period_low else 0.5
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=channel_position,
            reason=f"In channel ({channel_position:.0%} position, P/L: {unrealized_pnl_pct:.1%})",
            current_price=current_price,
            metadata={
                'period_high': period_high,
                'period_low': period_low,
                'channel_position': channel_position,
                'entry_price': entry_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
            }
        )

    def _analyze_without_position(
        self,
        symbol: str,
        current_price: float,
        period_high: float,
        period_low: float,
        breakout_level: float,
        breakdown_level: float
    ) -> TradingSignal:
        """Generate signal when not holding a position."""
        # Check for breakout (price breaks above high)
        if current_price > breakout_level:
            pct_above_high = (current_price - period_high) / period_high
            return TradingSignal(
                symbol=symbol,
                action=SignalType.BUY,
                strength=min(pct_above_high, 1.0),
                reason=f"Breakout above {self.lookback_days}-day high (${period_high:.2f})",
                current_price=current_price,
                metadata={
                    'period_high': period_high,
                    'period_low': period_low,
                    'breakout_level': breakout_level,
                    'pct_above_high': pct_above_high,
                }
            )

        # No signal - price in channel
        channel_position = (current_price - period_low) / (period_high - period_low) if period_high > period_low else 0.5
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=0.0,
            reason=f"In channel (${period_low:.2f} - ${period_high:.2f}, {channel_position:.0%} position)",
            current_price=current_price,
            metadata={
                'period_high': period_high,
                'period_low': period_low,
                'channel_position': channel_position,
            }
        )

    def get_parameters(self) -> dict:
        """Get current strategy parameters."""
        return {
            'lookback_days': self.lookback_days,
            'breakout_threshold': self.breakout_threshold,
            'breakdown_threshold': self.breakdown_threshold,
            'stop_loss_pct': self.stop_loss_pct,
        }
