#!/usr/bin/env python3
"""
Post-market backtest automation.

Runs after market close to:
1. Backtest today's strategy with actual parameters
2. Compare backtest vs live performance
3. Generate daily performance report
4. Export results for review

Usage:
    python scripts/post_market_backtest.py
    python scripts/post_market_backtest.py --period 30  # Last 30 days
    python scripts/post_market_backtest.py --download   # Download data first
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.metrics import compute_equity_metrics, compute_trade_outcomes
from analytics.store import AnalyticsStore
from backtest.data import HistoricalData
from backtest.engine import BacktestEngine
import config


def load_live_config():
    """Load current live trading configuration."""
    config_file = Path("data/config_state.json")
    if config_file.exists():
        with open(config_file) as f:
            state = json.load(f)
        return state.get("config", {})
    return {}


def get_symbols_to_test():
    """Get symbols from current watchlist and positions."""
    from universe import Universe

    # Load from config
    watchlist = config.WATCHLIST or []

    # Add any symbols we have positions in
    store = AnalyticsStore(Universe.SIMULATION)
    positions_data = store.load_equity(period="1d")

    symbols = set(watchlist)

    # Get unique symbols from recent data
    if not symbols:
        # Fallback to some default symbols if watchlist is empty
        symbols = {"AAPL", "GOOGL", "MSFT", "NVDA"}

    return sorted(list(symbols))


def load_live_analytics(period_days=30):
    """Load live trading analytics for comparison."""
    from universe import Universe

    store = AnalyticsStore(Universe.SIMULATION)

    # Load equity and trades
    period = f"{period_days}d"
    equity_points = store.load_equity(period=period)
    trades = store.load_trades(period=period, limit=1000)

    # Compute metrics
    equity_metrics = compute_equity_metrics(equity_points)
    trade_stats = compute_trade_outcomes(trades)

    return {
        "equity_metrics": equity_metrics,
        "trade_stats": trade_stats,
        "equity_points": equity_points,
        "trades": trades,
    }


def run_backtest(symbols, period_days=30, download=False):
    """Run backtest with current configuration."""
    live_config = load_live_config()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days + 10)  # Extra days for lookback

    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')

    # Initialize data
    data = HistoricalData()

    # Download if requested
    if download:
        print(f"Downloading data for {len(symbols)} symbols...")
        data.download(symbols=symbols, start=start_str, end=end_str, force=True)

        # Download benchmark
        if config.BENCHMARK_SYMBOL:
            print(f"Downloading benchmark {config.BENCHMARK_SYMBOL}...")
            data.download(
                symbols=[config.BENCHMARK_SYMBOL],
                start=start_str,
                end=end_str,
                force=True
            )

    # Load data
    print(f"Loading data for backtest ({start_str} to {end_str})...")
    loaded = data.load(symbols, start=start_str, end=end_str)

    if not loaded:
        print("ERROR: No data loaded. Run with --download to fetch historical data.")
        return None

    # Load benchmark
    benchmark_symbol = None
    if config.BENCHMARK_SYMBOL:
        bench_loaded = data.load([config.BENCHMARK_SYMBOL], start=start_str, end=end_str)
        if bench_loaded:
            benchmark_symbol = config.BENCHMARK_SYMBOL

    # Get strategy parameters from live config or defaults
    momentum_threshold = live_config.get("momentum_threshold", config.MOMENTUM_THRESHOLD)
    sell_threshold = live_config.get("sell_threshold", config.SELL_THRESHOLD)
    stop_loss = live_config.get("stop_loss", config.STOP_LOSS)
    max_position = live_config.get("max_position", config.MAX_POSITION_SIZE)

    # Create engine with live parameters
    engine = BacktestEngine(
        data=data,
        initial_capital=100000,  # Match paper trading starting capital
        commission=0.0,
        slippage=0.001,
        max_position_pct=max_position,
        stop_loss_pct=stop_loss,
    )

    engine.set_strategy_params(
        lookback_days=config.LOOKBACK_DAYS,
        momentum_threshold=momentum_threshold,
        sell_threshold=sell_threshold,
    )

    # Run backtest
    print(f"\nRunning backtest with live parameters:")
    print(f"  Momentum threshold: {momentum_threshold:.1%}")
    print(f"  Sell threshold: {sell_threshold:.1%}")
    print(f"  Stop loss: {stop_loss:.1%}")
    print(f"  Max position: {max_position:.1%}")
    print(f"  Lookback days: {config.LOOKBACK_DAYS}")
    print()

    results = engine.run(
        symbols=symbols,
        start=start_str,
        end=end_str,
        benchmark_symbol=benchmark_symbol,
    )

    return results


def compare_performance(backtest_results, live_analytics):
    """Compare backtest vs live performance."""
    print("\n" + "="*70)
    print("BACKTEST vs LIVE COMPARISON")
    print("="*70)

    # Backtest metrics
    bt_metrics = backtest_results.metrics

    # Live metrics
    live_equity = live_analytics["equity_metrics"]
    live_trades = live_analytics["trade_stats"]

    print("\n📊 PERFORMANCE METRICS")
    print("-" * 70)
    print(f"{'Metric':<25} {'Backtest':>15} {'Live':>15} {'Diff':>12}")
    print("-" * 70)

    # Total Return
    bt_return = bt_metrics.total_return * 100
    live_return = live_equity.total_return_pct
    diff_return = live_return - bt_return
    print(f"{'Total Return':<25} {bt_return:>14.2f}% {live_return:>14.2f}% {diff_return:>11.2f}%")

    # Max Drawdown
    bt_dd = bt_metrics.max_drawdown * 100
    live_dd = live_equity.max_drawdown_pct
    diff_dd = live_dd - bt_dd
    print(f"{'Max Drawdown':<25} {bt_dd:>14.2f}% {live_dd:>14.2f}% {diff_dd:>11.2f}%")

    # Sharpe Ratio
    bt_sharpe = bt_metrics.sharpe_ratio
    live_sharpe = live_equity.sharpe_ratio
    diff_sharpe = live_sharpe - bt_sharpe
    print(f"{'Sharpe Ratio':<25} {bt_sharpe:>15.2f} {live_sharpe:>15.2f} {diff_sharpe:>12.2f}")

    # Win Rate
    bt_win_rate = bt_metrics.win_rate * 100
    live_win_rate = live_trades.win_rate_pct
    diff_wr = live_win_rate - bt_win_rate
    print(f"{'Win Rate':<25} {bt_win_rate:>14.2f}% {live_win_rate:>14.2f}% {diff_wr:>11.2f}%")

    print("\n💼 TRADING ACTIVITY")
    print("-" * 70)
    print(f"{'Metric':<25} {'Backtest':>15} {'Live':>15}")
    print("-" * 70)
    print(f"{'Total Trades':<25} {bt_metrics.total_trades:>15} {live_trades.total:>15}")
    print(f"{'Winning Trades':<25} {bt_metrics.winning_trades:>15} {live_trades.win_trades:>15}")
    print(f"{'Losing Trades':<25} {bt_metrics.losing_trades:>15} {live_trades.loss_trades:>15}")

    # Performance assessment
    print("\n🎯 ASSESSMENT")
    print("-" * 70)

    drift_threshold = 5.0  # 5% difference is significant

    if abs(diff_return) > drift_threshold:
        status = "⚠️  SIGNIFICANT DRIFT"
        advice = "Live performance differs significantly from backtest. Investigate:"
        issues = []
        if diff_return < 0:
            issues.append("• Live underperforming - check fill prices, slippage, timing")
        else:
            issues.append("• Live outperforming - backtest may be too conservative")
        if abs(diff_wr) > 10:
            issues.append("• Win rate divergence - strategy behavior changed")
        print(f"{status}")
        print(advice)
        for issue in issues:
            print(issue)
    else:
        print("✅ Performance tracking as expected")
        print(f"Live vs backtest delta: {diff_return:+.2f}% (within {drift_threshold}% threshold)")

    print()


def export_results(backtest_results, output_dir="data/post_market"):
    """Export backtest results to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d')

    # Export JSON summary
    json_file = output_path / f"backtest_{timestamp}.json"
    backtest_results.to_json(str(json_file))
    print(f"📄 Exported summary: {json_file}")

    # Export equity curve
    equity_file = output_path / f"equity_{timestamp}.csv"
    backtest_results.to_csv(str(equity_file))
    print(f"📈 Exported equity: {equity_file}")

    # Export trades
    trades_file = output_path / f"trades_{timestamp}.csv"
    backtest_results.trades_to_csv(str(trades_file))
    print(f"📊 Exported trades: {trades_file}")

    print(f"\nAll results saved to: {output_path}/")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run post-market backtest and compare with live trading"
    )
    parser.add_argument(
        "--period",
        type=int,
        default=30,
        help="Number of days to backtest (default: 30)"
    )
    parser.add_argument(
        "--download", "-d",
        action="store_true",
        help="Download fresh historical data"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated symbols (default: uses current watchlist)"
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Skip exporting results to files"
    )

    args = parser.parse_args()

    # Print header
    print("\n" + "="*70)
    print(f"POST-MARKET BACKTEST ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    # Get symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        symbols = get_symbols_to_test()

    print(f"\n📋 Testing {len(symbols)} symbols: {', '.join(symbols)}")
    print(f"📅 Period: Last {args.period} days")

    # Run backtest
    backtest_results = run_backtest(
        symbols=symbols,
        period_days=args.period,
        download=args.download
    )

    if not backtest_results:
        return 1

    # Display backtest results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print(backtest_results.summary())

    # Load live analytics
    print("\nLoading live trading data...")
    live_analytics = load_live_analytics(period_days=args.period)

    # Compare performance
    compare_performance(backtest_results, live_analytics)

    # Export results
    if not args.no_export:
        export_results(backtest_results)

    print("\n✅ Post-market analysis complete!")
    print("="*70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
