"""
Performance metrics calculations for backtesting.

Provides standard financial performance metrics used to evaluate
trading strategy effectiveness.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# Annualization factor (trading days per year)
TRADING_DAYS_PER_YEAR = 252

# Risk-free rate (approximate, for Sharpe/Sortino calculations)
# Using 5% as a reasonable approximation for recent years
RISK_FREE_RATE = 0.05


@dataclass
class PerformanceMetrics:
    """Container for all performance metrics."""

    # Returns
    total_return: float
    total_return_pct: float
    annualized_return: float

    # Risk metrics
    volatility: float  # Annualized
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int  # Days

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    avg_trade: float
    largest_win: float
    largest_loss: float

    # Exposure
    exposure_time: float  # Percentage of time in market
    avg_position_duration: float  # Days

    # Benchmark comparison (optional)
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None

    # Risk limit diagnostics
    max_daily_loss: float = 0.0
    daily_loss_limit_hits: int = 0
    drawdown_limit_hit: bool = False

    def __str__(self) -> str:
        """Format metrics as a readable summary."""
        lines = [
            "Performance Metrics",
            "=" * 50,
            "",
            "Returns",
            "-" * 30,
            f"  Total Return:        ${self.total_return:,.2f} ({self.total_return_pct:.2%})",
            f"  Annualized Return:   {self.annualized_return:.2%}",
            "",
            "Risk Metrics",
            "-" * 30,
            f"  Volatility (Ann.):   {self.volatility:.2%}",
            f"  Sharpe Ratio:        {self.sharpe_ratio:.2f}",
            f"  Sortino Ratio:       {self.sortino_ratio:.2f}",
            f"  Max Drawdown:        {self.max_drawdown:.2%}",
            f"  Max DD Duration:     {self.max_drawdown_duration} days",
            f"  Worst Daily Return:  {self.max_daily_loss:.2%}",
            f"  Daily Loss Hits:     {self.daily_loss_limit_hits}",
            f"  Drawdown Limit Hit:  {'Yes' if self.drawdown_limit_hit else 'No'}",
            "",
            "Trade Statistics",
            "-" * 30,
            f"  Total Trades:        {self.total_trades}",
            f"  Winning Trades:      {self.winning_trades}",
            f"  Losing Trades:       {self.losing_trades}",
            f"  Win Rate:            {self.win_rate:.2%}",
            f"  Profit Factor:       {self.profit_factor:.2f}",
            f"  Avg Win:             ${self.avg_win:,.2f}",
            f"  Avg Loss:            ${self.avg_loss:,.2f}",
            f"  Avg Trade:           ${self.avg_trade:,.2f}",
            f"  Largest Win:         ${self.largest_win:,.2f}",
            f"  Largest Loss:        ${self.largest_loss:,.2f}",
            "",
            "Exposure",
            "-" * 30,
            f"  Time in Market:      {self.exposure_time:.2%}",
            f"  Avg Position Hold:   {self.avg_position_duration:.1f} days",
        ]

        if self.benchmark_return is not None:
            lines.extend([
                "",
                "Benchmark Comparison",
                "-" * 30,
                f"  Benchmark Return:    {self.benchmark_return:.2%}",
                f"  Alpha:               {self.alpha:.2%}" if self.alpha else "  Alpha:               N/A",
                f"  Beta:                {self.beta:.2f}" if self.beta else "  Beta:                N/A",
            ])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return {
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_duration': self.max_drawdown_duration,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'avg_trade': self.avg_trade,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'exposure_time': self.exposure_time,
            'avg_position_duration': self.avg_position_duration,
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha,
            'beta': self.beta,
            'max_daily_loss': self.max_daily_loss,
            'daily_loss_limit_hits': self.daily_loss_limit_hits,
            'drawdown_limit_hit': self.drawdown_limit_hit,
        }


def calculate_returns(equity_curve: pd.Series) -> pd.Series:
    """
    Calculate daily returns from equity curve.

    Args:
        equity_curve: Series of portfolio values indexed by date

    Returns:
        Series of daily returns
    """
    return equity_curve.pct_change().dropna()


def calculate_annualized_return(total_return_pct: float, num_days: int) -> float:
    """
    Calculate annualized return from total return.

    Args:
        total_return_pct: Total return as decimal (e.g., 0.15 for 15%)
        num_days: Number of trading days

    Returns:
        Annualized return as decimal
    """
    if num_days <= 0:
        return 0.0

    years = num_days / TRADING_DAYS_PER_YEAR
    if years <= 0:
        return 0.0

    # Compound annual growth rate
    return (1 + total_return_pct) ** (1 / years) - 1


def calculate_volatility(returns: pd.Series) -> float:
    """
    Calculate annualized volatility.

    Args:
        returns: Series of daily returns

    Returns:
        Annualized volatility as decimal
    """
    if len(returns) < 2:
        return 0.0

    return float(returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = RISK_FREE_RATE
) -> float:
    """
    Calculate Sharpe ratio.

    Sharpe = (Annualized Return - Risk Free Rate) / Annualized Volatility

    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sharpe ratio
    """
    if len(returns) < 2:
        return 0.0

    # Annualized mean return
    ann_return = float(returns.mean() * TRADING_DAYS_PER_YEAR)

    # Annualized volatility
    ann_vol = calculate_volatility(returns)

    if ann_vol == 0:
        return 0.0

    return (ann_return - risk_free_rate) / ann_vol


def calculate_sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = RISK_FREE_RATE
) -> float:
    """
    Calculate Sortino ratio.

    Like Sharpe but only considers downside volatility.

    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate

    Returns:
        Sortino ratio
    """
    if len(returns) < 2:
        return 0.0

    # Annualized mean return
    ann_return = float(returns.mean() * TRADING_DAYS_PER_YEAR)

    # Downside returns only
    downside_returns = returns[returns < 0]

    if len(downside_returns) < 2:
        # No downside volatility - return high value
        return 10.0 if ann_return > risk_free_rate else 0.0

    # Downside deviation (annualized)
    downside_std = float(downside_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))

    if downside_std == 0:
        return 10.0 if ann_return > risk_free_rate else 0.0

    return (ann_return - risk_free_rate) / downside_std


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, int]:
    """
    Calculate maximum drawdown and its duration.

    Drawdown is the peak-to-trough decline in portfolio value.

    Args:
        equity_curve: Series of portfolio values indexed by date

    Returns:
        Tuple of (max_drawdown_pct, max_drawdown_duration_days)
    """
    if len(equity_curve) < 2:
        return 0.0, 0

    # Running maximum
    running_max = equity_curve.expanding().max()

    # Drawdown at each point
    drawdown = (equity_curve - running_max) / running_max

    # Maximum drawdown
    max_dd = float(drawdown.min())

    # Calculate duration of maximum drawdown
    # Find when we hit the peak before max drawdown
    max_dd_idx = drawdown.idxmin()
    peak_idx = equity_curve[:max_dd_idx].idxmax()

    # Find when (if) we recovered
    recovery_mask = equity_curve[max_dd_idx:] >= equity_curve[peak_idx]
    if recovery_mask.any():
        recovery_idx = recovery_mask.idxmax()
        duration = (recovery_idx - peak_idx).days
    else:
        # Never recovered
        duration = (equity_curve.index[-1] - peak_idx).days

    return abs(max_dd), duration


def calculate_trade_statistics(trades: list[dict]) -> dict:
    """
    Calculate trade-level statistics.

    Args:
        trades: List of trade dictionaries with 'pnl' key

    Returns:
        Dictionary of trade statistics
    """
    if not trades:
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'avg_trade': 0.0,
            'largest_win': 0.0,
            'largest_loss': 0.0,
            'avg_position_duration': 0.0,
        }

    pnls = [t.get('pnl', 0) for t in trades]
    durations = [t.get('duration_days', 0) for t in trades]

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    total_wins = sum(wins) if wins else 0
    total_losses = abs(sum(losses)) if losses else 0

    return {
        'total_trades': len(trades),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': len(wins) / len(trades) if trades else 0.0,
        'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0.0,
        'avg_win': np.mean(wins) if wins else 0.0,
        'avg_loss': np.mean(losses) if losses else 0.0,
        'avg_trade': np.mean(pnls) if pnls else 0.0,
        'largest_win': max(wins) if wins else 0.0,
        'largest_loss': min(losses) if losses else 0.0,
        'avg_position_duration': np.mean(durations) if durations else 0.0,
    }


def calculate_exposure(
    position_series: pd.Series,
    equity_curve: pd.Series
) -> float:
    """
    Calculate time spent in market (exposure).

    Args:
        position_series: Series indicating position value at each date
        equity_curve: Series of portfolio values

    Returns:
        Exposure as decimal (e.g., 0.75 = 75% of time in market)
    """
    if len(position_series) == 0:
        return 0.0

    # Time with any position
    in_market = (position_series.abs() > 0).sum()
    total_days = len(position_series)

    return in_market / total_days if total_days > 0 else 0.0


def calculate_benchmark_comparison(
    strategy_returns: pd.Series,
    benchmark_returns: pd.Series
) -> dict:
    """
    Calculate alpha and beta relative to benchmark.

    Args:
        strategy_returns: Series of strategy daily returns
        benchmark_returns: Series of benchmark daily returns

    Returns:
        Dictionary with benchmark_return, alpha, and beta
    """
    # Align the series
    aligned = pd.concat([strategy_returns, benchmark_returns], axis=1).dropna()

    if len(aligned) < 30:  # Need sufficient data
        return {
            'benchmark_return': float(benchmark_returns.sum()) if len(benchmark_returns) > 0 else None,
            'alpha': None,
            'beta': None,
        }

    strat_ret = aligned.iloc[:, 0]
    bench_ret = aligned.iloc[:, 1]

    # Total benchmark return
    benchmark_total = float((1 + bench_ret).prod() - 1)

    # Calculate beta (covariance / variance)
    covariance = strat_ret.cov(bench_ret)
    variance = bench_ret.var()
    beta = covariance / variance if variance > 0 else 0.0

    # Calculate alpha (annualized)
    # Alpha = Strategy Return - (Risk-free Rate + Beta * (Benchmark Return - Risk-free Rate))
    strat_ann = float(strat_ret.mean() * TRADING_DAYS_PER_YEAR)
    bench_ann = float(bench_ret.mean() * TRADING_DAYS_PER_YEAR)
    alpha = strat_ann - (RISK_FREE_RATE + beta * (bench_ann - RISK_FREE_RATE))

    return {
        'benchmark_return': benchmark_total,
        'alpha': alpha,
        'beta': beta,
    }


def calculate_metrics(
    equity_curve: pd.Series,
    trades: list[dict],
    position_series: pd.Series,
    initial_capital: float,
    benchmark_returns: Optional[pd.Series] = None,
    daily_loss_limit_pct: Optional[float] = None,
    max_drawdown_limit_pct: Optional[float] = None,
) -> PerformanceMetrics:
    """
    Calculate all performance metrics.

    Args:
        equity_curve: Series of portfolio values indexed by date
        trades: List of trade dictionaries
        position_series: Series of position values
        initial_capital: Starting capital
        benchmark_returns: Optional benchmark daily returns for comparison

    Returns:
        PerformanceMetrics object with all calculated metrics
    """
    # Basic returns
    final_value = equity_curve.iloc[-1] if len(equity_curve) > 0 else initial_capital
    total_return = final_value - initial_capital
    total_return_pct = total_return / initial_capital

    num_days = len(equity_curve)
    ann_return = calculate_annualized_return(total_return_pct, num_days)

    # Daily returns
    daily_returns = calculate_returns(equity_curve)

    # Risk metrics
    volatility = calculate_volatility(daily_returns)
    sharpe = calculate_sharpe_ratio(daily_returns)
    sortino = calculate_sortino_ratio(daily_returns)
    max_dd, max_dd_duration = calculate_max_drawdown(equity_curve)

    max_daily_loss = float(daily_returns.min()) if len(daily_returns) > 0 else 0.0
    if daily_loss_limit_pct and daily_loss_limit_pct > 0:
        daily_loss_hits = int((daily_returns <= -daily_loss_limit_pct).sum())
    else:
        daily_loss_hits = 0
    drawdown_limit_hit = bool(max_drawdown_limit_pct and max_dd >= max_drawdown_limit_pct)

    # Trade statistics
    trade_stats = calculate_trade_statistics(trades)

    # Exposure
    exposure = calculate_exposure(position_series, equity_curve)

    # Benchmark comparison
    bench_comparison = {'benchmark_return': None, 'alpha': None, 'beta': None}
    if benchmark_returns is not None:
        bench_comparison = calculate_benchmark_comparison(daily_returns, benchmark_returns)

    return PerformanceMetrics(
        total_return=total_return,
        total_return_pct=total_return_pct,
        annualized_return=ann_return,
        volatility=volatility,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown=max_dd,
        max_drawdown_duration=max_dd_duration,
        total_trades=trade_stats['total_trades'],
        winning_trades=trade_stats['winning_trades'],
        losing_trades=trade_stats['losing_trades'],
        win_rate=trade_stats['win_rate'],
        profit_factor=trade_stats['profit_factor'],
        avg_win=trade_stats['avg_win'],
        avg_loss=trade_stats['avg_loss'],
        avg_trade=trade_stats['avg_trade'],
        largest_win=trade_stats['largest_win'],
        largest_loss=trade_stats['largest_loss'],
        exposure_time=exposure,
        avg_position_duration=trade_stats['avg_position_duration'],
        benchmark_return=bench_comparison['benchmark_return'],
        alpha=bench_comparison['alpha'],
        beta=bench_comparison['beta'],
        max_daily_loss=max_daily_loss,
        daily_loss_limit_hits=daily_loss_hits,
        drawdown_limit_hit=drawdown_limit_hit,
    )
