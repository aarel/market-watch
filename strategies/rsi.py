"""
RSI (Relative Strength Index) trading strategy.

Buys when RSI indicates oversold conditions and sells when
RSI indicates overbought conditions.
"""

import pandas as pd
from typing import Optional

from strategies.base import Strategy, TradingSignal, SignalType
import config


class RSIStrategy(Strategy):
    """
    RSI-based mean reversion strategy.

    **Logic:**
    - Calculate RSI (Relative Strength Index) over specified period
    - Buy when RSI crosses above oversold threshold (e.g., 30)
    - Sell when RSI crosses below overbought threshold (e.g., 70)
    - Apply stop-loss for risk management

    **Parameters:**
    - rsi_period: Number of periods for RSI calculation (default: 14)
    - oversold_level: RSI level considered oversold (default: 30)
    - overbought_level: RSI level considered overbought (default: 70)
    - stop_loss_pct: Maximum loss before automatic exit (default: 0.05 = 5%)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_level: float = 30,
        overbought_level: float = 70,
        stop_loss_pct: float = None
    ):
        """
        Initialize RSI strategy.

        Args:
            rsi_period: Period for RSI calculation
            oversold_level: Buy when RSI rises above this level
            overbought_level: Sell when RSI falls below this level
            stop_loss_pct: Stop loss percentage (default from config)
        """
        self.rsi_period = rsi_period
        self.oversold_level = oversold_level
        self.overbought_level = overbought_level
        self.stop_loss_pct = stop_loss_pct or config.STOP_LOSS_PCT

    @property
    def name(self) -> str:
        return "RSI Strategy"

    @property
    def description(self) -> str:
        return f"Buys when RSI({self.rsi_period}) > {self.oversold_level}, sells when < {self.overbought_level}"

    @property
    def required_history(self) -> int:
        return self.rsi_period + 10  # Need extra for reliable RSI calculation

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: float,
        current_position: Optional[dict] = None
    ) -> TradingSignal:
        """Generate trading signal based on RSI."""
        # Calculate RSI
        rsi = self._calculate_rsi(bars)

        has_position = current_position is not None

        if has_position:
            return self._analyze_with_position(
                symbol, current_price, rsi, current_position
            )
        else:
            return self._analyze_without_position(
                symbol, current_price, rsi
            )

    def _calculate_rsi(self, bars: pd.DataFrame) -> float:
        """
        Calculate RSI (Relative Strength Index).

        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

        Args:
            bars: Historical OHLCV data

        Returns:
            RSI value (0-100)
        """
        closes = bars['close']
        deltas = closes.diff()

        # Separate gains and losses
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)

        # Calculate average gains and losses using SMA
        avg_gains = gains.rolling(window=self.rsi_period).mean()
        avg_losses = losses.rolling(window=self.rsi_period).mean()

        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1])

    def _analyze_with_position(
        self,
        symbol: str,
        current_price: float,
        rsi: float,
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
                    'rsi': rsi,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'stop_loss'
                }
            )

        # Check for overbought condition (time to sell)
        if rsi >= self.overbought_level:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=(rsi - self.overbought_level) / (100 - self.overbought_level),
                reason=f"Overbought (RSI: {rsi:.1f})",
                current_price=current_price,
                metadata={
                    'rsi': rsi,
                    'entry_price': entry_price,
                    'unrealized_pnl_pct': unrealized_pnl_pct,
                    'trigger': 'overbought'
                }
            )

        # Hold position - waiting for overbought signal
        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=(rsi - self.oversold_level) / (self.overbought_level - self.oversold_level),
            reason=f"Holding (RSI: {rsi:.1f}, P/L: {unrealized_pnl_pct:.1%})",
            current_price=current_price,
            metadata={
                'rsi': rsi,
                'entry_price': entry_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
            }
        )

    def _analyze_without_position(
        self,
        symbol: str,
        current_price: float,
        rsi: float
    ) -> TradingSignal:
        """Generate signal when not holding a position."""
        # Check for oversold condition (buy signal)
        if rsi <= self.oversold_level:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.BUY,
                strength=(self.oversold_level - rsi) / self.oversold_level,
                reason=f"Oversold (RSI: {rsi:.1f})",
                current_price=current_price,
                metadata={
                    'rsi': rsi,
                    'rsi_period': self.rsi_period,
                }
            )

        # No signal
        if rsi < 50:
            condition = "weak"
        elif rsi < self.overbought_level:
            condition = "neutral"
        else:
            condition = "strong"

        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=0.0,
            reason=f"RSI {condition} ({rsi:.1f}, threshold: <{self.oversold_level})",
            current_price=current_price,
            metadata={
                'rsi': rsi,
            }
        )

    def get_parameters(self) -> dict:
        """Get current strategy parameters."""
        return {
            'rsi_period': self.rsi_period,
            'oversold_level': self.oversold_level,
            'overbought_level': self.overbought_level,
            'stop_loss_pct': self.stop_loss_pct,
        }
