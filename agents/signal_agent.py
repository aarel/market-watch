"""Signal Agent - generates trading signals from market data using pluggable strategies."""
import asyncio
import pandas as pd
from typing import TYPE_CHECKING

from .base import BaseAgent
from .events import MarketDataReady, SignalGenerated, SignalsUpdated
from strategies import Strategy, MomentumStrategy

if TYPE_CHECKING:
    from broker import AlpacaBroker
    from .event_bus import EventBus


class SignalAgent(BaseAgent):
    """
    Analyzes market data and generates trading signals using a strategy.

    The agent delegates signal generation to a pluggable Strategy instance,
    allowing for different trading strategies without changing the agent code.
    """

    def __init__(
        self,
        event_bus: "EventBus",
        broker: "AlpacaBroker",
        strategy: Strategy = None
    ):
        """
        Initialize SignalAgent.

        Args:
            event_bus: Event bus for agent communication
            broker: Broker interface for position lookups
            strategy: Trading strategy to use (defaults to MomentumStrategy)
        """
        super().__init__("SignalAgent", event_bus)
        self.broker = broker
        self.strategy = strategy or MomentumStrategy()
        self._last_signals = []

    async def start(self):
        """Start listening for market data events."""
        await super().start()
        self.event_bus.subscribe(MarketDataReady, self._handle_market_data)
        print(f"SignalAgent started with strategy: {self.strategy.name}")

    async def stop(self):
        """Stop the agent."""
        self.event_bus.unsubscribe(MarketDataReady, self._handle_market_data)
        await super().stop()

    async def _handle_market_data(self, event: MarketDataReady):
        """Process market data and generate signals."""
        from universe import Universe
        if not event.market_open and self.universe != Universe.SIMULATION:
            return

        signals = []

        for symbol in event.symbols:
            if symbol not in event.prices:
                continue

            current_price = event.prices[symbol]
            bars_data = event.bars.get(symbol, {})

            # Convert bars data to DataFrame for strategy
            bars_df = self._convert_bars_to_dataframe(bars_data)

            if bars_df is None or len(bars_df) < self.strategy.required_history:
                signals.append(SignalGenerated(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    symbol=symbol,
                    action="hold",
                    strength=0.0,
                    reason=f"Insufficient history (need {self.strategy.required_history} bars)",
                    current_price=current_price,
                    momentum=0.0,
                ))
                continue

            # Get current position info
            position_info = self._get_position_info(symbol)

            # Generate signal using strategy
            try:
                signal = self.strategy.analyze(
                    symbol=symbol,
                    bars=bars_df,
                    current_price=current_price,
                    current_position=position_info
                )

                # Convert TradingSignal to SignalGenerated event
                signal_event = SignalGenerated(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    symbol=signal.symbol,
                    action=signal.action.value,  # Convert enum to string
                    strength=signal.strength,
                    reason=signal.reason,
                    current_price=signal.current_price,
                    momentum=signal.metadata.get('momentum', 0.0),
                )

                signals.append(signal_event)

                # Emit event for actionable signals
                if signal.action.value != "hold":
                    await self.event_bus.publish(signal_event)

            except Exception as e:
                print(f"SignalAgent: Error generating signal for {symbol}: {e}")
                signals.append(SignalGenerated(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    symbol=symbol,
                    action="hold",
                    strength=0.0,
                    reason=f"Signal generation error: {e}",
                    current_price=current_price,
                    momentum=0.0,
                ))

        self._last_signals = signals
        await self.event_bus.publish(SignalsUpdated(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            signals=[
                {
                    "symbol": s.symbol,
                    "action": s.action,
                    "strength": s.strength,
                    "reason": s.reason,
                    "current_price": s.current_price,
                    "momentum": s.momentum,
                }
                for s in signals
            ],
        ))

    def _convert_bars_to_dataframe(self, bars_data: dict) -> pd.DataFrame:
        """
        Convert bars data from event to DataFrame format expected by strategies.

        Args:
            bars_data: Dictionary with close/open/high/low/volume keys

        Returns:
            DataFrame with OHLCV columns or None if insufficient data
        """
        try:
            if not bars_data or 'close' not in bars_data:
                return None

            # Extract data arrays
            close_dict = bars_data.get('close', {})
            open_dict = bars_data.get('open', {})
            high_dict = bars_data.get('high', {})
            low_dict = bars_data.get('low', {})
            volume_dict = bars_data.get('volume', {})

            if not close_dict:
                return None

            # Sort by index and convert to lists
            indices = sorted(close_dict.keys())
            close = [close_dict[i] for i in indices]
            open_prices = [open_dict.get(i, close_dict[i]) for i in indices]
            high = [high_dict.get(i, close_dict[i]) for i in indices]
            low = [low_dict.get(i, close_dict[i]) for i in indices]
            volume = [volume_dict.get(i, 0) for i in indices]

            # Create DataFrame
            df = pd.DataFrame({
                'open': open_prices,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
            })

            return df

        except Exception as e:
            print(f"SignalAgent: Error converting bars to DataFrame: {e}")
            return None

    def _get_position_info(self, symbol: str) -> dict:
        """
        Get current position information for a symbol.

        Args:
            symbol: Ticker symbol

        Returns:
            Position info dict or None if no position
        """
        try:
            position = self.broker.get_position(symbol)
            if position is None:
                return None

            entry_price = float(position.avg_entry_price)
            qty = float(position.qty)
            current_price = float(position.current_price)
            market_value = float(position.market_value)
            unrealized_pnl = float(position.unrealized_pl)
            unrealized_pnl_pct = unrealized_pnl / (entry_price * qty) if (entry_price * qty) > 0 else 0

            return {
                'quantity': qty,
                'entry_price': entry_price,
                'current_price': current_price,
                'market_value': market_value,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct,
            }

        except Exception as e:
            # Position doesn't exist or error occurred
            return None

    def set_strategy(self, strategy: Strategy):
        """
        Change the trading strategy dynamically.

        Args:
            strategy: New strategy instance to use
        """
        self.strategy = strategy
        print(f"SignalAgent: Strategy changed to {strategy.name}")

    def get_strategy(self) -> Strategy:
        """Get the current strategy instance."""
        return self.strategy

    def get_signals(self) -> list:
        """Get the most recent signals."""
        return self._last_signals

    def status(self) -> dict:
        """Get agent status."""
        base = super().status()
        base["strategy"] = self.strategy.name
        base["strategy_params"] = self.strategy.get_parameters()
        base["signal_count"] = len(self._last_signals)
        base["actionable"] = sum(1 for s in self._last_signals if s.action != "hold")
        return base
