"""Configuration management for the trading bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca settings
# Both Trading API and Market Data API use the same keys
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
# Universe is determined by TRADING_MODE: "live", "paper", or "simulation"
TRADING_MODE = os.getenv("TRADING_MODE", "paper")

SIMULATION_JIGGLE_FACTOR = float(os.getenv("SIMULATION_JIGGLE_FACTOR", "0.001"))
SIM_REPLAY_ENABLED = os.getenv("SIM_REPLAY_ENABLED", "false").lower() == "true"
SIM_REPLAY_DATE = os.getenv("SIM_REPLAY_DATE", "")

# Replay recorder (captures intraday bars for SIM)
REPLAY_RECORDER_ENABLED = os.getenv("REPLAY_RECORDER_ENABLED", "false").lower() == "true"
REPLAY_RECORDER_INTERVAL_MINUTES = int(os.getenv("REPLAY_RECORDER_INTERVAL_MINUTES", "5"))
# Default symbols use WATCHLIST once defined; set placeholder first
_default_replay_symbols = os.getenv("REPLAY_RECORDER_SYMBOLS", "")
REPLAY_RECORDER_DIR = os.getenv("REPLAY_RECORDER_DIR", "data/replay")

# Market data feed: "iex" (free) or "sip" (paid - requires Algo Trader Plus)
DATA_FEED = os.getenv("DATA_FEED", "iex")

# API endpoints (Trading API - Market Data API is handled by the library)
ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"
ALPACA_LIVE_URL = "https://api.alpaca.markets"

def get_alpaca_url():
    """Return the appropriate Alpaca API URL based on trading mode."""
    if TRADING_MODE == "live":
        return ALPACA_LIVE_URL
    return ALPACA_PAPER_URL

# Trading parameters
WATCHLIST = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA"]  # Default watchlist
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.5"))  # Max % of portfolio in single position
MIN_TRADE_VALUE = 1.0   # Minimum trade value in dollars

# Finalize replay recorder symbols now that WATCHLIST is defined
REPLAY_RECORDER_SYMBOLS = [
    s.strip().upper()
    for s in (_default_replay_symbols or ",".join(WATCHLIST)).split(",")
    if s.strip()
]

# Watchlist mode: "static" or "top_gainers"
WATCHLIST_MODE = os.getenv("WATCHLIST_MODE", "top_gainers")
TOP_GAINERS_COUNT = int(os.getenv("TOP_GAINERS_COUNT", "20"))
TOP_GAINERS_UNIVERSE = os.getenv("TOP_GAINERS_UNIVERSE", "large_cap")
TOP_GAINERS_MIN_PRICE = float(os.getenv("TOP_GAINERS_MIN_PRICE", "5"))
TOP_GAINERS_MIN_VOLUME = int(os.getenv("TOP_GAINERS_MIN_VOLUME", "1000000"))

# Market index proxies for UI ticker (ETFs)
MARKET_INDEX_SYMBOLS = [
    symbol.strip().upper()
    for symbol in os.getenv(
        "MARKET_INDEX_SYMBOLS",
        "SPY,QQQ,DIA,IVV,VOO,IWM,SMH,XLF,XLK,XLY,XLI,XLE,XLV,XLB,XLU,XLRE,XLC"
    ).split(",")
    if symbol.strip()
]

# Strategy selection
# Available: "momentum", "mean_reversion", "breakout", "rsi"
STRATEGY = os.getenv("STRATEGY", "momentum").lower()

# Momentum strategy parameters
LOOKBACK_DAYS = 30       # Days to calculate momentum (RSI needs 25 bars minimum)
MOMENTUM_THRESHOLD = float(os.getenv("MOMENTUM_THRESHOLD", "0.02"))  # % momentum threshold to trigger buy
SELL_THRESHOLD = float(os.getenv("SELL_THRESHOLD", "-0.01"))  # % momentum to trigger sell

# Risk controls
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", "5"))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.05"))  # Stop loss percentage
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "20"))
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "0.03"))
MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", "0.15"))
MAX_SECTOR_EXPOSURE_PCT = float(os.getenv("MAX_SECTOR_EXPOSURE_PCT", "1.00"))
MAX_CORRELATED_EXPOSURE_PCT = float(os.getenv("MAX_CORRELATED_EXPOSURE_PCT", "1.00"))
CORRELATION_THRESHOLD = float(os.getenv("CORRELATION_THRESHOLD", "0.8"))
CORRELATION_LOOKBACK_DAYS = int(os.getenv("CORRELATION_LOOKBACK_DAYS", "30"))
RVOL_THRESHOLD = float(os.getenv("RVOL_THRESHOLD", "2.0"))  # Relative volume threshold
SECTOR_MAP_PATH = os.getenv("SECTOR_MAP_PATH", "data/shared/sector_map.json")
SECTOR_MAP_JSON = os.getenv("SECTOR_MAP_JSON", "")

# Position sizing
POSITION_SIZER_SCALE_BY_STRENGTH = os.getenv("POSITION_SIZER_SCALE_BY_STRENGTH", "true").lower() == "true"
POSITION_SIZER_MIN_STRENGTH = float(os.getenv("POSITION_SIZER_MIN_STRENGTH", "0.0"))
POSITION_SIZER_MAX_STRENGTH = float(os.getenv("POSITION_SIZER_MAX_STRENGTH", "1.0"))

# Notification
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
REQUIRE_APPROVAL = os.getenv("REQUIRE_APPROVAL", "false").lower() == "true"

# Security
API_TOKEN = os.getenv("API_TOKEN", "")
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if origin.strip()
]

# Web server
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
UI_PORT = int(os.getenv("UI_PORT", "3000"))

# Auto-trading
AUTO_TRADE = os.getenv("AUTO_TRADE", "true").lower() == "true"
TRADE_INTERVAL_MINUTES = int(os.getenv("TRADE_INTERVAL_MINUTES", "5"))

# Market timezone for daily limits (IANA timezone name)
MARKET_TIMEZONE = os.getenv("MARKET_TIMEZONE", "America/New_York")

# Observability (system-level logs)
OBSERVABILITY_ENABLED = os.getenv("OBSERVABILITY_ENABLED", "true").lower() == "true"
OBSERVABILITY_LOG_PATH = os.getenv(
    "OBSERVABILITY_LOG_PATH",
    "logs/system/agent_events.jsonl",
)
OBSERVABILITY_MAX_LOG_MB = float(os.getenv("OBSERVABILITY_MAX_LOG_MB", "5"))

# Alerts
ALERTS_ENABLED = os.getenv("ALERTS_ENABLED", "false").lower() == "true"
ALERT_EMAIL_ENABLED = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
ALERT_WEBHOOK_ENABLED = os.getenv("ALERT_WEBHOOK_ENABLED", "false").lower() == "true"

# Email alert channel
ALERT_EMAIL_SMTP_HOST = os.getenv("ALERT_EMAIL_SMTP_HOST", "")
ALERT_EMAIL_SMTP_PORT = int(os.getenv("ALERT_EMAIL_SMTP_PORT", "587"))
ALERT_EMAIL_SMTP_USER = os.getenv("ALERT_EMAIL_SMTP_USER", "")
ALERT_EMAIL_SMTP_PASSWORD = os.getenv("ALERT_EMAIL_SMTP_PASSWORD", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_EMAIL_USE_TLS = os.getenv("ALERT_EMAIL_USE_TLS", "true").lower() == "true"
ALERT_EMAIL_RETRY_ATTEMPTS = int(os.getenv("ALERT_EMAIL_RETRY_ATTEMPTS", "3"))

# Webhook alert channel
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
ALERT_WEBHOOK_TYPE = os.getenv("ALERT_WEBHOOK_TYPE", "generic")
ALERT_WEBHOOK_RETRY_ATTEMPTS = int(os.getenv("ALERT_WEBHOOK_RETRY_ATTEMPTS", "3"))
ALERT_WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("ALERT_WEBHOOK_TIMEOUT_SECONDS", "10"))

# UI check agent (system-level logs)
UI_CHECK_ENABLED = os.getenv("UI_CHECK_ENABLED", "false").lower() == "true"
UI_CHECK_INTERVAL_MINUTES = int(os.getenv("UI_CHECK_INTERVAL_MINUTES", "30"))
UI_CHECK_URL = os.getenv("UI_CHECK_URL", "")
UI_CHECK_LOG_PATH = os.getenv("UI_CHECK_LOG_PATH", "logs/system/ui_checks.jsonl")

# Automated testing agent (system-level logs)
TEST_AGENT_ENABLED = os.getenv("TEST_AGENT_ENABLED", "false").lower() == "true"
TEST_AGENT_INTERVAL_MINUTES = int(os.getenv("TEST_AGENT_INTERVAL_MINUTES", "180"))
TEST_AGENT_LOG_PATH = os.getenv("TEST_AGENT_LOG_PATH", "logs/system/tests.jsonl")

# Runtime config persistence
CONFIG_STATE_PATH = os.getenv("CONFIG_STATE_PATH", "data/config_state.json")

# Analytics & reporting
ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
# DEPRECATED: AnalyticsStore now uses universe-scoped paths (logs/{universe}/)
# ANALYTICS_DATA_PATH = os.getenv("ANALYTICS_DATA_PATH", "data/analytics")
