"""
Backtest simulation engine.

The core engine that replays historical data through a strategy,
simulating order execution and tracking portfolio performance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol

import pandas as pd
import numpy as np

from backtest.data import HistoricalData
from backtest.metrics import calculate_metrics, PerformanceMetrics
from backtest.results import BacktestResults, Trade
import config


class StrategyProtocol(Protocol):
    """Protocol defining what the engine expects from a strategy."""

    def calculate_momentum(self, symbol: str, bars: pd.DataFrame) -> float:
        """Calculate momentum from historical bars."""
        ...


@dataclass
class Position:
    """Represents a position in a symbol."""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return self.unrealized_pnl / self.cost_basis


@dataclass
class BacktestBroker:
    """
    Simulated broker for backtesting.

    Provides a broker-like interface that the strategy can use,
    but backed by historical data instead of live market data.
    """
    data: HistoricalData
    current_date: datetime = None
    lookback_days: int = 20

    def get_bars(self, symbol: str, days: int = None) -> Optional[pd.DataFrame]:
        """
        Get historical bars up to current backtest date.

        This prevents lookahead bias by only returning data
        that would have been available at the current date.
        """
        if days is None:
            days = self.lookback_days

        if self.current_date is None:
            return None

        return self.data.get_bars_up_to(
            symbol,
            pd.Timestamp(self.current_date),
            days
        )

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the closing price for the current date."""
        return self.data.get_price(
            symbol,
            pd.Timestamp(self.current_date),
            'close'
        )

    def get_position(self, symbol: str) -> None:
        """
        Stub for compatibility with strategy.

        In backtesting, positions are managed by the engine,
        not queried from a broker.
        """
        return None


@dataclass
class BacktestState:
    """Tracks the state of a backtest simulation."""

    initial_capital: float
    cash: float = 0.0
    positions: dict = field(default_factory=dict)  # symbol -> Position

    # History tracking
    equity_history: list = field(default_factory=list)  # (date, value) tuples
    position_history: list = field(default_factory=list)  # (date, positions_value) tuples
    trades: list = field(default_factory=list)  # Completed Trade objects
    open_trades: dict = field(default_factory=dict)  # symbol -> Trade (in progress)

    def __post_init__(self):
        self.cash = self.initial_capital

    @property
    def positions_value(self) -> float:
        """Total market value of all positions."""
        return sum(p.market_value for p in self.positions.values())

    @property
    def equity(self) -> float:
        """Total portfolio value (cash + positions)."""
        return self.cash + self.positions_value

    def update_prices(self, prices: dict[str, float]):
        """Update current prices for all positions."""
        for symbol, position in self.positions.items():
            if symbol in prices and prices[symbol] is not None:
                position.current_price = prices[symbol]

    def record_state(self, date: datetime):
        """Record current state for history."""
        self.equity_history.append((date, self.equity))
        self.position_history.append((date, self.positions_value))


class BacktestEngine:
    """
    Event-driven backtesting engine.

    Simulates trading by iterating through historical data day by day,
    generating signals from the strategy, and executing simulated trades.

    Key principles:
    - No lookahead bias: strategy only sees data up to current bar
    - Realistic execution: orders execute at next day's open price
    - Commission and slippage modeling
    """

    def __init__(
        self,
        data: HistoricalData,
        initial_capital: float = 100000,
        commission: float = 0.0,
        slippage: float = 0.001,
        max_position_pct: float = 0.25,
        stop_loss_pct: float = 0.05,
    ):
        """
        Initialize the backtest engine.

        Args:
            data: HistoricalData instance with loaded price data
            initial_capital: Starting cash amount
            commission: Commission per trade as decimal (0.001 = 0.1%)
            slippage: Slippage assumption as decimal (0.001 = 0.1%)
            max_position_pct: Maximum position size as % of portfolio
            stop_loss_pct: Stop loss percentage for positions
        """
        self.data = data
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct

        # Strategy parameters (can be overridden)
        self.lookback_days = config.LOOKBACK_DAYS
        self.momentum_threshold = config.MOMENTUM_THRESHOLD
        self.sell_threshold = config.SELL_THRESHOLD

    def run(
        self,
        symbols: Optional[list[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        benchmark_symbol: Optional[str] = None,
    ) -> BacktestResults:
        """
        Run the backtest simulation.

        Args:
            symbols: List of symbols to trade (defaults to all loaded)
            start: Start date YYYY-MM-DD (defaults to data start)
            end: End date YYYY-MM-DD (defaults to data end)
            benchmark_symbol: Symbol to compare against (e.g., 'SPY')

        Returns:
            BacktestResults object with all results
        """
        # Determine symbols
        if symbols is None:
            symbols = self.data.symbols
        symbols = [s.upper() for s in symbols]

        # Determine date range
        data_start, data_end = self.data.date_range
        if start:
            start_date = pd.Timestamp(start)
        else:
            start_date = data_start
        if end:
            end_date = pd.Timestamp(end)
        else:
            end_date = data_end

        print(f"Running backtest: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Initial capital: ${self.initial_capital:,.2f}")

        # Get all trading dates from the data
        all_dates = set()
        for symbol in symbols:
            df = self.data.get(symbol)
            if df is not None:
                symbol_dates = df.index[(df.index >= start_date) & (df.index <= end_date)]
                all_dates.update(symbol_dates)

        trading_dates = sorted(all_dates)

        if not trading_dates:
            raise ValueError("No trading dates found in the specified range")

        print(f"Trading days: {len(trading_dates)}")

        # Initialize state
        state = BacktestState(initial_capital=self.initial_capital)

        # Create simulated broker for strategy
        broker = BacktestBroker(
            data=self.data,
            lookback_days=self.lookback_days
        )

        # Skip first N days to build up history for momentum calculation
        warmup_days = self.lookback_days + 5
        if len(trading_dates) <= warmup_days:
            raise ValueError(f"Insufficient data: need at least {warmup_days} days for warmup")

        # Main simulation loop
        for i, date in enumerate(trading_dates):
            broker.current_date = date

            # Get current prices for all symbols
            prices = {}
            for symbol in symbols:
                price = self.data.get_price(symbol, date, 'close')
                if price is not None:
                    prices[symbol] = price

            # Update position prices
            state.update_prices(prices)

            # Skip warmup period
            if i < warmup_days:
                state.record_state(date)
                continue

            # Check stop losses first
            self._check_stop_losses(state, prices, date)

            # Generate signals and execute trades
            for symbol in symbols:
                if symbol not in prices:
                    continue

                signal = self._generate_signal(
                    symbol, broker, state, prices[symbol]
                )

                if signal == 'buy' and symbol not in state.positions:
                    self._execute_buy(state, symbol, prices[symbol], date)
                elif signal == 'sell' and symbol in state.positions:
                    self._execute_sell(state, symbol, prices[symbol], date, "Momentum reversal")

            # Record state
            state.record_state(date)

        # Close any remaining positions at end
        final_date = trading_dates[-1]
        for symbol in list(state.positions.keys()):
            price = self.data.get_price(symbol, final_date, 'close')
            if price:
                self._execute_sell(state, symbol, price, final_date, "End of backtest")

        # Build results
        return self._build_results(
            state,
            symbols,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            benchmark_symbol
        )

    def _generate_signal(
        self,
        symbol: str,
        broker: BacktestBroker,
        state: BacktestState,
        current_price: float
    ) -> str:
        """
        Generate a trading signal for a symbol.

        This replicates the logic from MomentumStrategy but uses
        the backtest broker for data access.
        """
        # Get historical bars
        bars = broker.get_bars(symbol, self.lookback_days)
        if bars is None or len(bars) < 2:
            return 'hold'

        # Calculate momentum
        current_close = bars['close'].iloc[-1]
        past_close = bars['close'].iloc[0]
        momentum = (current_close - past_close) / past_close

        # Check if we have a position
        has_position = symbol in state.positions

        if has_position:
            position = state.positions[symbol]

            # Check for sell signals
            if momentum < self.sell_threshold:
                return 'sell'

            return 'hold'
        else:
            # Check for buy signals
            if momentum > self.momentum_threshold:
                return 'buy'

            return 'hold'

    def _check_stop_losses(
        self,
        state: BacktestState,
        prices: dict[str, float],
        date: datetime
    ):
        """Check and execute stop losses for all positions."""
        for symbol in list(state.positions.keys()):
            position = state.positions[symbol]
            if symbol not in prices:
                continue

            current_price = prices[symbol]
            position.current_price = current_price

            if position.unrealized_pnl_pct <= -self.stop_loss_pct:
                self._execute_sell(
                    state, symbol, current_price, date,
                    f"Stop loss ({position.unrealized_pnl_pct:.1%})"
                )

    def _execute_buy(
        self,
        state: BacktestState,
        symbol: str,
        price: float,
        date: datetime
    ):
        """Execute a buy order."""
        # Apply slippage (buy at slightly higher price)
        execution_price = price * (1 + self.slippage)

        # Calculate position size
        max_value = state.equity * self.max_position_pct
        available_cash = state.cash * 0.95  # Keep 5% cash buffer

        position_value = min(max_value, available_cash)
        if position_value < 100:  # Minimum trade size
            return

        quantity = int(position_value / execution_price)
        if quantity < 1:
            return

        # Calculate cost including commission
        cost = quantity * execution_price
        commission_cost = cost * self.commission
        total_cost = cost + commission_cost

        if total_cost > state.cash:
            return

        # Execute
        state.cash -= total_cost
        state.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=execution_price,
            entry_date=date,
            current_price=execution_price
        )

        # Record open trade
        state.open_trades[symbol] = Trade(
            symbol=symbol,
            side='buy',
            entry_date=date,
            entry_price=execution_price,
            quantity=quantity,
            reason=f"Momentum above {self.momentum_threshold:.1%}"
        )

    def _execute_sell(
        self,
        state: BacktestState,
        symbol: str,
        price: float,
        date: datetime,
        reason: str
    ):
        """Execute a sell order."""
        if symbol not in state.positions:
            return

        position = state.positions[symbol]

        # Apply slippage (sell at slightly lower price)
        execution_price = price * (1 - self.slippage)

        # Calculate proceeds
        proceeds = position.quantity * execution_price
        commission_cost = proceeds * self.commission
        net_proceeds = proceeds - commission_cost

        # Calculate P&L
        cost_basis = position.quantity * position.entry_price
        pnl = net_proceeds - cost_basis
        pnl_pct = pnl / cost_basis if cost_basis > 0 else 0

        # Execute
        state.cash += net_proceeds
        del state.positions[symbol]

        # Complete the trade record
        if symbol in state.open_trades:
            trade = state.open_trades[symbol]
            trade.exit_date = date
            trade.exit_price = execution_price
            trade.pnl = pnl
            trade.pnl_pct = pnl_pct
            trade.duration_days = (date - trade.entry_date).days
            trade.reason = reason
            state.trades.append(trade)
            del state.open_trades[symbol]

    def _build_results(
        self,
        state: BacktestState,
        symbols: list[str],
        start_date: str,
        end_date: str,
        benchmark_symbol: Optional[str]
    ) -> BacktestResults:
        """Build the BacktestResults object from simulation state."""

        # Build equity curve
        equity_df = pd.DataFrame(
            state.equity_history,
            columns=['date', 'value']
        ).set_index('date')
        equity_curve = equity_df['value']

        # Build position history
        position_df = pd.DataFrame(
            state.position_history,
            columns=['date', 'value']
        ).set_index('date')
        position_series = position_df['value']

        # Get benchmark returns if specified
        benchmark_returns = None
        if benchmark_symbol and benchmark_symbol in self.data.symbols:
            bench_data = self.data.get(benchmark_symbol)
            if bench_data is not None:
                bench_data = bench_data[
                    (bench_data.index >= pd.Timestamp(start_date)) &
                    (bench_data.index <= pd.Timestamp(end_date))
                ]
                benchmark_returns = bench_data['close'].pct_change().dropna()

        # Calculate metrics
        trade_dicts = [
            {
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'duration_days': t.duration_days
            }
            for t in state.trades
        ]

        metrics = calculate_metrics(
            equity_curve=equity_curve,
            trades=trade_dicts,
            position_series=position_series,
            initial_capital=self.initial_capital,
            benchmark_returns=benchmark_returns,
            daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
            max_drawdown_limit_pct=config.MAX_DRAWDOWN_PCT,
        )

        return BacktestResults(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            strategy_name="MomentumStrategy",
            strategy_params={
                'lookback_days': self.lookback_days,
                'momentum_threshold': self.momentum_threshold,
                'sell_threshold': self.sell_threshold,
                'stop_loss_pct': self.stop_loss_pct,
                'max_position_pct': self.max_position_pct,
                'commission': self.commission,
                'slippage': self.slippage,
            },
            metrics=metrics,
            equity_curve=equity_curve,
            trades=state.trades,
            position_history=position_df,
            benchmark_symbol=benchmark_symbol,
        )

    def set_strategy_params(
        self,
        lookback_days: Optional[int] = None,
        momentum_threshold: Optional[float] = None,
        sell_threshold: Optional[float] = None,
        stop_loss_pct: Optional[float] = None,
        max_position_pct: Optional[float] = None,
    ):
        """
        Update strategy parameters.

        Allows running multiple backtests with different parameters
        without recreating the engine.
        """
        if lookback_days is not None:
            self.lookback_days = lookback_days
        if momentum_threshold is not None:
            self.momentum_threshold = momentum_threshold
        if sell_threshold is not None:
            self.sell_threshold = sell_threshold
        if stop_loss_pct is not None:
            self.stop_loss_pct = stop_loss_pct
        if max_position_pct is not None:
            self.max_position_pct = max_position_pct
