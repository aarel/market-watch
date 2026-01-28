"""
Mean reversion trading strategy.

Buys when price deviates significantly below its moving average
and sells when price returns to or exceeds the average.
"""

import pandas as pd
from typing import Optional

from strategies.base import Strategy, TradingSignal, SignalType
import config


class MeanReversionStrategy(Strategy):
    """
    Mean reversion strategy based on moving average deviation.

    **Logic:**
    - Calculate simple moving average over lookback period
    - Buy when price drops below MA by deviation threshold
    - Sell when price returns to MA or above
    - Apply stop-loss for risk management

    **Parameters:**
    - ma_period: Moving average period in days (default: 20)
    - deviation_threshold: % below MA to trigger buy (default: 0.03 = 3%)
    - return_threshold: % above MA to trigger sell (default: 0.01 = 1%)
    - stop_loss_pct: Maximum loss before automatic exit (default: 0.05 = 5%)
    """

    def __init__(
        self,
        ma_period: int = 20,
        deviation_threshold: float = 0.03,
        return_threshold: float = 0.01,
        stop_loss_pct: float = None
    ):
        """
        Initialize mean reversion strategy.

        Args:
            ma_period: Moving average period
            deviation_threshold: Buy when price is this % below MA
            return_threshold: Sell when price is this % above MA
            stop_loss_pct: Stop loss percentage (default from config)
        """
        self.ma_period = ma_period
        self.deviation_threshold = deviation_threshold
        self.return_threshold = return_threshold
        self.stop_loss_pct = stop_loss_pct or config.STOP_LOSS_PCT

    @property
    def name(self) -> str:
        return "Mean Reversion Strategy"

    @property
    def description(self) -> str:
        return f"Buys when price is >{self.deviation_threshold:.1%} below {self.ma_period}-day MA, sells on return"

    @property
    def required_history(self) -> int:
        return self.ma_period + 5  # Need extra for reliable MA calculation

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: float,
        current_position: Optional[dict] = None
    ) -> TradingSignal:
        """Generate trading signal based on mean reversion."""
        # Calculate moving average
        ma = bars['close'].rolling(window=self.ma_period).mean().iloc[-1]

        # Calculate deviation from MA
        deviation = (current_price - ma) / ma

        has_position = current_position is not None

        if has_position:
            return self._analyze_with_position(
                symbol, current_price, ma, deviation, current_position
            )
        else:
            return self._analyze_without_position(
                symbol, current_price, ma, deviation
            )

    def _analyze_with_position(
        self,
        symbol: str,
        current_price: float,
        ma: float,
        deviation: float,
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
                    'ma': ma,
                    'deviation': deviation,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'stop_loss'
                }
            )

        # Check if price returned to MA (mean reversion complete)
        if deviation >= self.return_threshold:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=abs(deviation),
                reason=f"Price returned to MA ({deviation:+.1%} from MA)",
                current_price=current_price,
                metadata={
                    'ma': ma,
                    'deviation': deviation,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'mean_reversion'
                }
            )

        # Hold position - waiting for reversion
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=abs(deviation),
            reason=f"Waiting for reversion ({deviation:+.1%} from MA, P/L: {unrealized_pnl_pct:.1%})",
            current_price=current_price,
            metadata={
                'ma': ma,
                'deviation': deviation,
                'entry_price': entry_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
            }
        )

    def _analyze_without_position(
        self,
        symbol: str,
        current_price: float,
        ma: float,
        deviation: float
    ) -> TradingSignal:
        """Generate signal when not holding a position."""
        # Check for buy signal - price significantly below MA
        if deviation < -self.deviation_threshold:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.BUY,
                strength=abs(deviation),
                reason=f"Price {deviation:.1%} below {self.ma_period}-day MA (oversold)",
                current_price=current_price,
                metadata={
                    'ma': ma,
                    'deviation': deviation,
                    'ma_period': self.ma_period,
                }
            )

        # No signal
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=abs(deviation),
            reason=f"Price near MA ({deviation:+.1%}, threshold: {-self.deviation_threshold:.1%})",
            current_price=current_price,
            metadata={
                'ma': ma,
                'deviation': deviation,
            }
        )

    def get_parameters(self) -> dict:
        """Get current strategy parameters."""
        return {
            'ma_period': self.ma_period,
            'deviation_threshold': self.deviation_threshold,
            'return_threshold': self.return_threshold,
            'stop_loss_pct': self.stop_loss_pct,
        }
