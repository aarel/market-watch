# Post-Market Backtest Automation

Automatically run backtests after market close to validate live trading performance.

## Quick Start

### 1. First-Time Setup

Run the interactive setup script:

```bash
./scripts/setup_cron.sh
```

This will:
- Create a wrapper script with logging
- Prompt you to choose a schedule (recommended: 4:30 PM ET)
- Add a cron job to run automatically weekdays
- Optionally run a test

### 2. Manual Test Run

To run manually before setting up automation:

```bash
# Basic run (uses current watchlist, last 30 days)
python scripts/post_market_backtest.py

# Download fresh data first
python scripts/post_market_backtest.py --download

# Custom period (last 60 days)
python scripts/post_market_backtest.py --period 60

# Specific symbols
python scripts/post_market_backtest.py --symbols AAPL,GOOGL,MSFT --download
```

## What It Does

The post-market automation:

1. **Loads Live Configuration** - Uses your current strategy parameters
2. **Runs Backtest** - Tests the strategy on recent historical data
3. **Compares Performance** - Shows backtest vs live metrics side-by-side
4. **Detects Drift** - Alerts if live performance diverges significantly
5. **Exports Results** - Saves to `data/post_market/` for review

## Output

### Console Report

```
======================================================================
POST-MARKET BACKTEST ANALYSIS - 2026-01-24 16:30:00
======================================================================

📋 Testing 15 symbols: AAPL, GOOGL, MSFT, ...
📅 Period: Last 30 days

Running backtest with live parameters:
  Momentum threshold: 3.0%
  Sell threshold: -1.5%
  Stop loss: 5.0%
  Max position: 15.0%
  Lookback days: 20

======================================================================
BACKTEST RESULTS
======================================================================
Total Return: +12.34%
Max Drawdown: -3.21%
Sharpe Ratio: 1.85
Win Rate: 62.50%
Total Trades: 48

======================================================================
BACKTEST vs LIVE COMPARISON
======================================================================

📊 PERFORMANCE METRICS
----------------------------------------------------------------------
Metric                      Backtest            Live         Diff
----------------------------------------------------------------------
Total Return                  +12.34%        +11.89%      -0.45%
Max Drawdown                   -3.21%         -3.45%      -0.24%
Sharpe Ratio                     1.85            1.78       -0.07
Win Rate                       62.50%         60.42%      -2.08%

💼 TRADING ACTIVITY
----------------------------------------------------------------------
Metric                      Backtest            Live
----------------------------------------------------------------------
Total Trades                      48              52
Winning Trades                    30              31
Losing Trades                     18              21

🎯 ASSESSMENT
----------------------------------------------------------------------
✅ Performance tracking as expected
Live vs backtest delta: -0.45% (within 5.0% threshold)
```

### Exported Files

All results saved to `data/post_market/`:

- `backtest_YYYYMMDD.json` - Complete results in JSON format
- `equity_YYYYMMDD.csv` - Equity curve data
- `trades_YYYYMMDD.csv` - Trade-by-trade log

### Logs

Execution logs saved to `logs/post_market_YYYYMMDD_HHMMSS.log`

## Drift Detection

The script alerts you if live performance differs significantly from backtest:

**⚠️  SIGNIFICANT DRIFT** triggered when:
- Return difference > 5%
- Win rate difference > 10%

**Possible causes:**
- Fill prices worse than backtest assumptions
- Timing differences (live vs historical close prices)
- Slippage higher than expected
- Strategy logic bugs
- Market regime change

## Schedule Recommendations

| Time | Pros | Cons |
|------|------|------|
| **4:30 PM ET** ✅ | Fresh data, results ready for evening review | May catch incomplete data on volatile days |
| **5:00 PM ET** | Data fully settled | Delays results by 30 min |
| **6:00 PM ET** | All data guaranteed settled | Results come later in evening |

**Recommended:** 4:30 PM ET (30 min after market close)

## Troubleshooting

### Cron not running on WSL

WSL doesn't start cron automatically. Fix:

```bash
# Start cron service
sudo service cron start

# Make it start on boot - add to /etc/wsl.conf:
[boot]
command = service cron start
```

### "No data loaded" error

Run with `--download` to fetch historical data:

```bash
python scripts/post_market_backtest.py --download
```

### View logs

```bash
# Latest log
tail -f logs/post_market_*.log

# All logs from today
ls -lt logs/post_market_$(date +%Y%m%d)*.log
```

### Remove cron job

```bash
crontab -e
# Delete the line containing: run_post_market.sh
```

## Advanced Usage

### Compare specific date ranges

```bash
# Last week only
python scripts/post_market_backtest.py --period 7

# Last quarter
python scripts/post_market_backtest.py --period 90
```

### Skip file export (console only)

```bash
python scripts/post_market_backtest.py --no-export
```

### Chain with other scripts

```bash
# Run backtest, then generate report, then email results
./scripts/run_post_market.sh && python -m reports generate --today && ./scripts/email_report.sh
```

## Integration with Other Tools

### Export to Google Sheets / Excel

The CSV files can be imported directly:
- Open Google Sheets / Excel
- File → Import → Choose `data/post_market/equity_YYYYMMDD.csv`

### Slack/Discord Notifications

Add to wrapper script (`run_post_market.sh`):

```bash
# After the backtest runs
if [ $EXIT_CODE -eq 0 ]; then
    curl -X POST YOUR_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d '{"text": "✅ Post-market backtest complete"}'
fi
```

### Dashboard Integration

Parse the JSON output in your monitoring dashboard:

```python
import json

with open('data/post_market/backtest_20260124.json') as f:
    results = json.load(f)

sharpe = results['metrics']['sharpe_ratio']
# Display on dashboard
```

## Files Created

```
scripts/
├── post_market_backtest.py    # Main automation script
├── setup_cron.sh               # Interactive cron setup
├── run_post_market.sh          # Wrapper with logging (auto-generated)
└── README.md                   # This file

data/
└── post_market/                # Daily backtest results
    ├── backtest_20260124.json
    ├── equity_20260124.csv
    └── trades_20260124.csv

logs/
└── post_market_*.log           # Execution logs
```
