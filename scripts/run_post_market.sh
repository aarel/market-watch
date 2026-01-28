#!/bin/bash
# Wrapper script for post-market backtest with logging

cd "/mnt/c/Users/aarel/Documents/coding/market-watch"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Run with logging
LOG_FILE="logs/post_market_$(date +%Y%m%d_%H%M%S).log"
echo "========================================" >> "$LOG_FILE"
echo "Post-Market Backtest - $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

"$PYTHON_PATH" scripts/post_market_backtest.py --period 30 >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Backtest completed successfully" >> "$LOG_FILE"
else
    echo "❌ Backtest failed with exit code $EXIT_CODE" >> "$LOG_FILE"
fi

# Keep only last 30 days of logs
find "/mnt/c/Users/aarel/Documents/coding/market-watch/logs" -name "post_market_*.log" -mtime +30 -delete

exit $EXIT_CODE
