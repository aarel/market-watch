#!/bin/bash
# Setup cron job for post-market backtest automation

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Post-Market Backtest Automation Setup"
echo "=========================================="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if running on WSL
if grep -qi microsoft /proc/version; then
    echo "⚠️  WARNING: Detected WSL environment"
    echo ""
    echo "WSL cron requires special setup:"
    echo "1. Cron may not start automatically on WSL"
    echo "2. You may need to start cron service manually"
    echo ""
    echo "To start cron on WSL:"
    echo "  sudo service cron start"
    echo ""
    echo "To make it start on boot, add this to /etc/wsl.conf:"
    echo "  [boot]"
    echo "  command = service cron start"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create log directory
mkdir -p "$PROJECT_DIR/logs"

# Verify WSL venv exists
PYTHON_PATH="$PROJECT_DIR/.venv-wsl/bin/python"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "ERROR: WSL venv not found at $PYTHON_PATH"
    echo "Run:  cd $PROJECT_DIR && python3 -m venv .venv-wsl && .venv-wsl/bin/pip install -r requirements.txt"
    exit 1
fi

echo "Using Python: $PYTHON_PATH"

# Create wrapper script for logging
WRAPPER_SCRIPT="$SCRIPT_DIR/run_post_market.sh"
cat > "$WRAPPER_SCRIPT" <<EOF
#!/bin/bash
# Wrapper script for post-market backtest with logging

PROJECT_DIR="$PROJECT_DIR"
PYTHON="$PYTHON_PATH"
cd "\$PROJECT_DIR"

# Run with logging
LOG_FILE="logs/post_market_\$(date +%Y%m%d_%H%M%S).log"
echo "========================================" >> "\$LOG_FILE"
echo "Post-Market Backtest - \$(date)" >> "\$LOG_FILE"
echo "========================================" >> "\$LOG_FILE"

"\$PYTHON" scripts/post_market_backtest.py --period 30 >> "\$LOG_FILE" 2>&1

EXIT_CODE=\$?

if [ \$EXIT_CODE -eq 0 ]; then
    echo "✅ Backtest completed successfully" >> "\$LOG_FILE"
else
    echo "❌ Backtest failed with exit code \$EXIT_CODE" >> "\$LOG_FILE"
fi

# Keep only last 30 days of logs
find "\$PROJECT_DIR/logs" -name "post_market_*.log" -mtime +30 -delete

exit \$EXIT_CODE
EOF

chmod +x "$WRAPPER_SCRIPT"
echo "✅ Created wrapper script: $WRAPPER_SCRIPT"

# Cron schedule options
echo ""
echo "Select schedule for post-market backtest:"
echo "  1) 4:30 PM ET (30 min after market close) - Recommended"
echo "  2) 5:00 PM ET (1 hour after close)"
echo "  3) 6:00 PM ET (2 hours after close)"
echo "  4) Custom time"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        # 4:30 PM ET = 16:30 local time (adjust for timezone)
        CRON_TIME="30 16"
        TIME_DESC="4:30 PM ET"
        ;;
    2)
        # 5:00 PM ET
        CRON_TIME="0 17"
        TIME_DESC="5:00 PM ET"
        ;;
    3)
        # 6:00 PM ET
        CRON_TIME="0 18"
        TIME_DESC="6:00 PM ET"
        ;;
    4)
        read -p "Enter hour (0-23): " hour
        read -p "Enter minute (0-59): " minute
        CRON_TIME="$minute $hour"
        TIME_DESC="$hour:$minute"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Build cron entry (Mon-Fri only)
CRON_ENTRY="$CRON_TIME * * 1-5 $WRAPPER_SCRIPT"

echo ""
echo "Cron entry to be added:"
echo "  $CRON_ENTRY"
echo ""
echo "This will run:"
echo "  - Every weekday (Monday-Friday)"
echo "  - At $TIME_DESC"
echo "  - Logs saved to: $PROJECT_DIR/logs/"
echo ""

read -p "Add this cron job? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cron job added successfully!"
    echo ""
    echo "To verify:"
    echo "  crontab -l"
    echo ""
    echo "To view logs:"
    echo "  tail -f $PROJECT_DIR/logs/post_market_*.log"
    echo ""
    echo "To remove this cron job:"
    echo "  crontab -e"
    echo "  (then delete the line containing: run_post_market.sh)"
    echo ""
else
    echo "❌ Failed to add cron job"
    exit 1
fi

# Test run option
echo ""
read -p "Run a test now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running test..."
    echo "=========================================="
    $WRAPPER_SCRIPT
    echo "=========================================="
    echo ""
    echo "Check the log file in $PROJECT_DIR/logs/"
fi

# ── log rotation cron jobs ────────────────────────────────────────────────────
# Daily:  5:00 AM ET  — move yesterday's completed logs into logs/weekly/
# Weekly: Sun 11:59 PM ET — archive logs/weekly/ into logs/archive/YYYY-MM/
#
# ET cron note: cron runs in system time.  These entries assume the system
# clock is set to US/Eastern (common in WSL when Windows is ET).  If your
# system is UTC, shift the hours accordingly (EDT: +4, EST: +5).

ROTATE_SCRIPT="$PROJECT_DIR/scripts/rotate_logs.py"
DAILY_ROTATE="0 5 * * * $PYTHON_PATH $ROTATE_SCRIPT --daily"
WEEKLY_ROTATE="59 23 * * 0 $PYTHON_PATH $ROTATE_SCRIPT --weekly"

echo ""
echo "=========================================="
echo "Log Rotation Setup"
echo "=========================================="
echo ""
echo "Cron entries to add:"
echo "  $DAILY_ROTATE"
echo "  $WEEKLY_ROTATE"
echo ""

read -p "Add log rotation cron jobs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    (crontab -l 2>/dev/null; echo "$DAILY_ROTATE"; echo "$WEEKLY_ROTATE") | crontab -
    if [ $? -eq 0 ]; then
        echo "✅ Log rotation cron jobs added"
    else
        echo "❌ Failed to add log rotation cron jobs"
    fi
else
    echo "Skipped log rotation cron jobs"
fi

echo ""
echo "✅ Setup complete!"
