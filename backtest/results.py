"""
Backtest results formatting and export.

Provides the BacktestResults class for storing, formatting,
and exporting backtest results in various formats.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from backtest.metrics import PerformanceMetrics


@dataclass
class Trade:
    """Record of a single trade."""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration_days: int = 0
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'entry_price': self.entry_price,
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'duration_days': self.duration_days,
            'reason': self.reason,
        }


@dataclass
class BacktestResults:
    """
    Container for backtest results.

    Stores all outputs from a backtest run including:
    - Configuration used
    - Equity curve
    - Trade log
    - Performance metrics
    """

    # Configuration
    symbols: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    strategy_name: str
    strategy_params: dict

    # Results
    metrics: PerformanceMetrics
    equity_curve: pd.Series
    trades: list[Trade]
    position_history: pd.DataFrame

    # Metadata
    run_timestamp: datetime = field(default_factory=datetime.now)
    benchmark_symbol: Optional[str] = None

    def summary(self) -> str:
        """Generate a formatted summary of the backtest."""
        lines = [
            "",
            "=" * 60,
            "BACKTEST RESULTS",
            "=" * 60,
            "",
            "Configuration",
            "-" * 40,
            f"  Strategy:        {self.strategy_name}",
            f"  Symbols:         {', '.join(self.symbols)}",
            f"  Period:          {self.start_date} to {self.end_date}",
            f"  Initial Capital: ${self.initial_capital:,.2f}",
            f"  Final Value:     ${self.initial_capital + self.metrics.total_return:,.2f}",
        ]

        if self.strategy_params:
            lines.append(f"  Parameters:")
            for key, value in self.strategy_params.items():
                lines.append(f"    {key}: {value}")

        lines.append("")
        lines.append(str(self.metrics))

        if self.trades:
            lines.extend([
                "",
                "Recent Trades (last 10)",
                "-" * 40,
            ])
            for trade in self.trades[-10:]:
                pnl_str = f"+${trade.pnl:.2f}" if trade.pnl >= 0 else f"-${abs(trade.pnl):.2f}"
                exit_price = trade.exit_price if trade.exit_price else 0.0
                lines.append(
                    f"  {trade.entry_date.strftime('%Y-%m-%d')} "
                    f"{trade.side.upper():4} {trade.symbol:5} "
                    f"@ ${trade.entry_price:.2f} -> ${exit_price:.2f} "
                    f"({pnl_str})"
                )

        lines.extend([
            "",
            "=" * 60,
            f"Run completed: {self.run_timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
        ])

        return "\n".join(lines)

    def to_csv(self, filepath: str):
        """
        Export equity curve to CSV.

        Args:
            filepath: Path for the output CSV file
        """
        df = pd.DataFrame({
            'date': self.equity_curve.index,
            'portfolio_value': self.equity_curve.values,
        })
        df.to_csv(filepath, index=False)
        print(f"Equity curve exported to {filepath}")

    def trades_to_csv(self, filepath: str):
        """
        Export trade log to CSV.

        Args:
            filepath: Path for the output CSV file
        """
        if not self.trades:
            print("No trades to export")
            return

        df = pd.DataFrame([t.to_dict() for t in self.trades])
        df.to_csv(filepath, index=False)
        print(f"Trade log exported to {filepath} ({len(self.trades)} trades)")

    def to_json(self, filepath: str):
        """
        Export full results to JSON.

        Args:
            filepath: Path for the output JSON file
        """
        data = {
            'config': {
                'symbols': self.symbols,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'initial_capital': self.initial_capital,
                'strategy_name': self.strategy_name,
                'strategy_params': self.strategy_params,
                'benchmark_symbol': self.benchmark_symbol,
            },
            'metrics': self.metrics.to_dict(),
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': {
                'dates': [d.isoformat() for d in self.equity_curve.index],
                'values': list(self.equity_curve.values),
            },
            'run_timestamp': self.run_timestamp.isoformat(),
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Full results exported to {filepath}")

    def to_dict(self) -> dict:
        """Convert results to dictionary."""
        return {
            'config': {
                'symbols': self.symbols,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'initial_capital': self.initial_capital,
                'strategy_name': self.strategy_name,
                'strategy_params': self.strategy_params,
            },
            'metrics': self.metrics.to_dict(),
            'trades': [t.to_dict() for t in self.trades],
        }

    @classmethod
    def from_json(cls, filepath: str) -> 'BacktestResults':
        """
        Load results from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            BacktestResults object
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct equity curve
        equity_curve = pd.Series(
            data['equity_curve']['values'],
            index=pd.to_datetime(data['equity_curve']['dates'])
        )

        # Reconstruct trades
        trades = []
        for t in data.get('trades', []):
            trade = Trade(
                symbol=t['symbol'],
                side=t['side'],
                entry_date=datetime.fromisoformat(t['entry_date']) if t['entry_date'] else None,
                entry_price=t['entry_price'],
                exit_date=datetime.fromisoformat(t['exit_date']) if t.get('exit_date') else None,
                exit_price=t.get('exit_price'),
                quantity=t.get('quantity', 0),
                pnl=t.get('pnl', 0),
                pnl_pct=t.get('pnl_pct', 0),
                duration_days=t.get('duration_days', 0),
                reason=t.get('reason', ''),
            )
            trades.append(trade)

        # Reconstruct metrics
        m = data['metrics']
        metrics = PerformanceMetrics(
            total_return=m['total_return'],
            total_return_pct=m['total_return_pct'],
            annualized_return=m['annualized_return'],
            volatility=m['volatility'],
            sharpe_ratio=m['sharpe_ratio'],
            sortino_ratio=m['sortino_ratio'],
            max_drawdown=m['max_drawdown'],
            max_drawdown_duration=m['max_drawdown_duration'],
            total_trades=m['total_trades'],
            winning_trades=m['winning_trades'],
            losing_trades=m['losing_trades'],
            win_rate=m['win_rate'],
            profit_factor=m['profit_factor'],
            avg_win=m['avg_win'],
            avg_loss=m['avg_loss'],
            avg_trade=m['avg_trade'],
            largest_win=m['largest_win'],
            largest_loss=m['largest_loss'],
            exposure_time=m['exposure_time'],
            avg_position_duration=m['avg_position_duration'],
            benchmark_return=m.get('benchmark_return'),
            alpha=m.get('alpha'),
            beta=m.get('beta'),
            max_daily_loss=m.get('max_daily_loss', 0.0),
            daily_loss_limit_hits=m.get('daily_loss_limit_hits', 0),
            drawdown_limit_hit=m.get('drawdown_limit_hit', False),
        )

        config = data['config']
        return cls(
            symbols=config['symbols'],
            start_date=config['start_date'],
            end_date=config['end_date'],
            initial_capital=config['initial_capital'],
            strategy_name=config['strategy_name'],
            strategy_params=config.get('strategy_params', {}),
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            position_history=pd.DataFrame(),  # Not persisted in JSON
            run_timestamp=datetime.fromisoformat(data.get('run_timestamp', datetime.now().isoformat())),
            benchmark_symbol=config.get('benchmark_symbol'),
        )

    def print_monthly_returns(self):
        """Print monthly returns table."""
        if len(self.equity_curve) < 2:
            print("Insufficient data for monthly returns")
            return

        # Resample to monthly
        monthly = self.equity_curve.resample('ME').last()
        monthly_returns = monthly.pct_change().dropna()

        # Create pivot table by year and month
        df = pd.DataFrame({
            'year': monthly_returns.index.year,
            'month': monthly_returns.index.month,
            'return': monthly_returns.values
        })

        pivot = df.pivot(index='year', columns='month', values='return')
        pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][:len(pivot.columns)]

        # Add yearly total
        pivot['Year'] = pivot.sum(axis=1)

        print("\nMonthly Returns")
        print("-" * 60)
        print(pivot.to_string(float_format=lambda x: f"{x:.1%}" if pd.notna(x) else ""))
