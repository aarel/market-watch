"""
Command-line interface for backtesting.

Usage:
    python -m backtest --symbols AAPL,GOOGL --start 2021-01-01 --end 2023-12-31
    python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2020-01-01
    python -m backtest --list-cached
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from backtest.data import HistoricalData
from backtest.engine import BacktestEngine


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Backtest trading strategies with historical data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download historical data
  python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2020-01-01

  # Run a backtest
  python -m backtest --symbols AAPL,GOOGL --start 2021-01-01 --end 2023-12-31

  # Run with custom parameters
  python -m backtest --symbols AAPL,GOOGL,MSFT,NVDA --start 2022-01-01 \\
      --capital 50000 --momentum-threshold 0.03 --lookback 15

  # Compare against benchmark
  python -m backtest --symbols AAPL,GOOGL --benchmark SPY --start 2021-01-01

  # Export results
  python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 \\
      --output results.json --trades-csv trades.csv

  # List cached data
  python -m backtest --list-cached
        """
    )

    # Actions
    action_group = parser.add_argument_group("Actions")
    action_group.add_argument(
        "--download", "-d",
        action="store_true",
        help="Download historical data (requires Alpaca credentials)"
    )
    action_group.add_argument(
        "--list-cached",
        action="store_true",
        help="List symbols with cached data"
    )
    action_group.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cached data (use with --symbols to clear specific symbols)"
    )

    # Data options
    data_group = parser.add_argument_group("Data Options")
    data_group.add_argument(
        "--symbols", "-s",
        type=str,
        help="Comma-separated list of symbols (e.g., AAPL,GOOGL,MSFT)"
    )
    data_group.add_argument(
        "--start",
        type=str,
        help="Start date in YYYY-MM-DD format"
    )
    data_group.add_argument(
        "--end",
        type=str,
        help="End date in YYYY-MM-DD format (defaults to today)"
    )
    data_group.add_argument(
        "--benchmark",
        type=str,
        help="Benchmark symbol to compare against (e.g., SPY)"
    )

    # Strategy parameters
    strategy_group = parser.add_argument_group("Strategy Parameters")
    strategy_group.add_argument(
        "--capital",
        type=float,
        default=100000,
        help="Initial capital (default: 100000)"
    )
    strategy_group.add_argument(
        "--lookback",
        type=int,
        default=20,
        help="Lookback period in days for momentum calculation (default: 20)"
    )
    strategy_group.add_argument(
        "--momentum-threshold",
        type=float,
        default=0.02,
        help="Momentum threshold to trigger buy (default: 0.02 = 2%%)"
    )
    strategy_group.add_argument(
        "--sell-threshold",
        type=float,
        default=-0.01,
        help="Momentum threshold to trigger sell (default: -0.01 = -1%%)"
    )
    strategy_group.add_argument(
        "--stop-loss",
        type=float,
        default=0.05,
        help="Stop loss percentage (default: 0.05 = 5%%)"
    )
    strategy_group.add_argument(
        "--max-position",
        type=float,
        default=0.25,
        help="Maximum position size as %% of portfolio (default: 0.25 = 25%%)"
    )
    strategy_group.add_argument(
        "--commission",
        type=float,
        default=0.0,
        help="Commission per trade as decimal (default: 0.0)"
    )
    strategy_group.add_argument(
        "--slippage",
        type=float,
        default=0.001,
        help="Slippage assumption as decimal (default: 0.001 = 0.1%%)"
    )

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for results (JSON format)"
    )
    output_group.add_argument(
        "--equity-csv",
        type=str,
        help="Export equity curve to CSV"
    )
    output_group.add_argument(
        "--trades-csv",
        type=str,
        help="Export trade log to CSV"
    )
    output_group.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress detailed output"
    )
    output_group.add_argument(
        "--monthly",
        action="store_true",
        help="Show monthly returns table"
    )

    return parser.parse_args()


def main():
    """Main entry point for CLI."""
    args = parse_args()

    # Initialize data manager
    data = HistoricalData()

    # Handle list-cached action
    if args.list_cached:
        cached = data.list_cached()
        if cached:
            print("Cached symbols:")
            for symbol in cached:
                df = data._load_cache(symbol)
                if df is not None:
                    start = df.index.min().strftime('%Y-%m-%d')
                    end = df.index.max().strftime('%Y-%m-%d')
                    print(f"  {symbol}: {len(df)} bars ({start} to {end})")
        else:
            print("No cached data found")
        return 0

    # Handle clear-cache action
    if args.clear_cache:
        symbols = args.symbols.split(',') if args.symbols else None
        data.clear_cache(symbols)
        print("Cache cleared")
        return 0

    # Parse symbols
    if not args.symbols:
        print("Error: --symbols is required")
        print("Usage: python -m backtest --symbols AAPL,GOOGL --start 2021-01-01")
        return 1

    symbols = [s.strip().upper() for s in args.symbols.split(',')]

    # Handle download action
    if args.download:
        if not args.start:
            print("Error: --start date is required for download")
            return 1

        print(f"Downloading data for: {', '.join(symbols)}")
        data.download(
            symbols=symbols,
            start=args.start,
            end=args.end,
            force=True
        )

        # Also download benchmark if specified
        if args.benchmark and args.benchmark.upper() not in symbols:
            print(f"Downloading benchmark: {args.benchmark}")
            data.download(
                symbols=[args.benchmark.upper()],
                start=args.start,
                end=args.end,
                force=True
            )

        print("Download complete")
        return 0

    # Run backtest
    if not args.start:
        print("Error: --start date is required")
        return 1

    # Load data (from cache or download)
    print("Loading historical data...")
    loaded = data.load(symbols, start=args.start, end=args.end)

    if not loaded:
        print("No data loaded. Run with --download first to fetch historical data.")
        print(f"  python -m backtest --download --symbols {args.symbols} --start {args.start}")
        return 1

    # Load benchmark if specified
    if args.benchmark:
        bench_symbol = args.benchmark.upper()
        if bench_symbol not in loaded:
            bench_loaded = data.load([bench_symbol], start=args.start, end=args.end)
            if not bench_loaded:
                print(f"Warning: Could not load benchmark {bench_symbol}")
                args.benchmark = None

    # Create and configure engine
    engine = BacktestEngine(
        data=data,
        initial_capital=args.capital,
        commission=args.commission,
        slippage=args.slippage,
        max_position_pct=args.max_position,
        stop_loss_pct=args.stop_loss,
    )

    engine.set_strategy_params(
        lookback_days=args.lookback,
        momentum_threshold=args.momentum_threshold,
        sell_threshold=args.sell_threshold,
    )

    # Run the backtest
    print()
    results = engine.run(
        symbols=symbols,
        start=args.start,
        end=args.end,
        benchmark_symbol=args.benchmark.upper() if args.benchmark else None,
    )

    # Display results
    if not args.quiet:
        print(results.summary())

        if args.monthly:
            results.print_monthly_returns()

    # Export results
    if args.output:
        results.to_json(args.output)

    if args.equity_csv:
        results.to_csv(args.equity_csv)

    if args.trades_csv:
        results.trades_to_csv(args.trades_csv)

    return 0


if __name__ == "__main__":
    sys.exit(main())
