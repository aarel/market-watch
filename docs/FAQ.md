# Frequently Asked Questions

> Common questions about Market-Watch trading bot

## Table of Contents

1. [General](#general)
2. [Getting Started](#getting-started)
3. [Trading](#trading)
4. [Strategies](#strategies)
5. [Backtesting](#backtesting)
6. [Configuration](#configuration)
7. [Technical](#technical)
8. [Troubleshooting](#troubleshooting)
9. [Safety & Risk](#safety--risk)

---

## General

### What is Market-Watch?

Market-Watch is an autonomous trading bot that:
- Executes momentum and other strategies automatically
- Works with Alpaca brokerage (paper and live trading)
- Provides web UI for monitoring and manual control
- Includes backtesting for strategy validation

### Is it free?

Yes, Market-Watch is open source. You'll need:
- Alpaca account (free paper trading, commission-free live trading)
- Server to run it (can be your computer)

### Do I need coding experience?

**To use it:** No, just follow setup instructions

**To customize:** Basic Python helpful for:
- Creating custom strategies
- Modifying risk rules
- Advanced configuration

### Is this production-ready?

**Current status:**
- ✅ Functional for paper trading
- ✅ Core features stable
- ⚠️ Use caution with real money
- 🚧 Some features still in development (see ROADMAP.md)

### Can I make money with this?

**Reality check:**
- Past performance ≠ future results
- Markets are unpredictable
- Most traders lose money
- Backtesting can be misleading

**Use this for:**
- Learning algorithmic trading
- Automating your own strategies
- Paper trading practice

**Not recommended for:**
- Get-rich-quick schemes
- Trading with money you can't afford to lose
- Expecting guaranteed returns

---

## Getting Started

### What do I need to get started?

1. **Python 3.10+** on your computer
2. **Alpaca account** (sign up at alpaca.markets)
3. **API keys** from Alpaca dashboard
4. **Basic terminal knowledge** (optional but helpful)

### How long does setup take?

- **Quick start:** 10 minutes (if you have API keys)
- **Full setup with backtesting:** 30 minutes
- **Production deployment:** 1-2 hours

### Can I test without real money?

**Yes! Three ways:**

1. **Paper Trading** (recommended):
   ```bash
   TRADING_MODE=paper python server.py
   ```
   Uses real market data, simulated execution

2. **Simulation Mode:**
   ```bash
   SIMULATION_MODE=true python server.py
   ```
   No API needed, random price data

3. **Backtesting:**
   ```bash
   python -m backtest --symbols AAPL --start 2022-01-01
   ```
   Test strategies on historical data

### Where do I get Alpaca API keys?

1. Sign up at https://alpaca.markets
2. Go to dashboard → Paper Trading → API Keys
3. Generate new keys
4. Copy to `.env` file

---

## Trading

### When does the bot trade?

**Market hours:** 9:30 AM - 4:00 PM ET (Monday-Friday)

**Trading cycle:**
1. Fetches data every N minutes (default: 5)
2. Generates signals
3. Executes approved trades
4. Monitors positions

**Configuration:**
```bash
TRADE_INTERVAL_MINUTES=5  # How often to check
AUTO_TRADE=true           # Enable auto-trading
```

### How do I enable/disable auto-trading?

**Via environment variable:**
```bash
AUTO_TRADE=false  # Disabled
AUTO_TRADE=true   # Enabled
```

**Via API:**
```bash
# Enable
curl -X POST http://localhost:8000/api/bot/start

# Disable
curl -X POST http://localhost:8000/api/bot/stop
```

**Via Web UI:** Click Start/Stop button

### How much does it trade?

**Position Sizing:**
- Default: 25% of portfolio per position (`MAX_POSITION_PCT=0.25`)
- Maximum 4 concurrent positions
- Respects available buying power

**Example with $10,000:**
- Max per position: $2,500
- If 4 positions: $10,000 total (fully invested)

**Daily Limits:**
```bash
MAX_DAILY_TRADES=5  # Maximum trades per day
```

### Can I manually execute trades?

**Yes, three ways:**

1. **Web UI:** Enter symbol, select buy/sell, click Execute

2. **API:**
   ```bash
   curl -X POST http://localhost:8000/api/trade \
     -H "Content-Type: application/json" \
     -d '{"symbol": "AAPL", "action": "buy", "amount": 1000}'
   ```

3. **Alpaca Dashboard:** Direct access

### What happens if the bot stops running?

- **Open positions:** Remain open (nothing happens)
- **Stop-losses:** Not enforced while bot is down
- **Auto-trading:** Resumes when bot restarts

**Best practice:** Use Alpaca's native stop-loss orders for safety

### Can it short stocks?

**Not currently.** The bot only:
- Buys stocks (long positions)
- Sells stocks (closes positions)

**Future enhancement:** Short selling could be added

---

## Strategies

### What strategies are available?

1. **Momentum** - Buys strong trends, sells on reversal
2. **Mean Reversion** - Buys oversold, sells on bounce
3. **Breakout** - Buys breakouts above highs
4. **RSI** - Buys oversold RSI, sells overbought

See [STRATEGIES.md](STRATEGIES.md) for details.

### How do I change strategies?

**Set in `.env` file:**
```bash
STRATEGY=momentum        # Default
# OR
STRATEGY=mean_reversion
# OR
STRATEGY=breakout
# OR
STRATEGY=rsi
```

**Restart server** after changing.

### Which strategy is best?

**It depends on market conditions:**

| Market | Best Strategy |
|--------|--------------|
| Strong trend | Momentum |
| Sideways/choppy | Mean Reversion, RSI |
| Volatile breakout | Breakout |
| Range-bound | RSI |

**Recommendation:** Backtest all strategies, choose based on results.

### Can I create custom strategies?

**Yes!** See [STRATEGIES.md](STRATEGIES.md) for tutorial.

**Steps:**
1. Create `strategies/my_strategy.py`
2. Inherit from `Strategy` base class
3. Implement `analyze()` method
4. Register in `strategies/__init__.py`
5. Use with `STRATEGY=my_strategy`

### How do I adjust strategy parameters?

**In `.env` file:**
```bash
# Momentum strategy
LOOKBACK_DAYS=20            # Period for calculation
MOMENTUM_THRESHOLD=0.02     # 2% buy threshold
SELL_THRESHOLD=-0.01        # -1% sell threshold

# Risk controls
STOP_LOSS_PCT=0.05          # 5% stop loss
MAX_POSITION_PCT=0.25       # 25% max position
```

**Via API (temporary):**
```bash
curl -X POST http://localhost:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{"momentum_threshold": 0.03, "stop_loss_pct": 0.03}'
```

---

## Backtesting

### Why should I backtest?

**Before risking real money, backtest to:**
- Validate strategy logic
- Measure historical performance
- Identify weaknesses
- Compare strategies
- Optimize parameters

### How do I run a backtest?

```bash
# 1. Download historical data
python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2020-01-01

# 2. Run backtest
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2021-01-01 --benchmark SPY

# 3. Export results
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 \
  --output results.json --trades-csv trades.csv
```

See [BACKTEST.md](BACKTEST.md) for full documentation.

### What metrics should I look at?

**Key metrics:**

| Metric | Good Value | Meaning |
|--------|-----------|---------|
| Sharpe Ratio | > 1.0 | Risk-adjusted return |
| Max Drawdown | < 20% | Worst loss from peak |
| Win Rate | 40-60% | % of profitable trades |
| Profit Factor | > 1.5 | Wins vs losses ratio |

**Red flags:**
- Sharpe < 0.5 (poor risk/reward)
- Max drawdown > 30% (too risky)
- < 20 trades (insufficient data)
- Win rate > 90% (probably overfit)

### How long should I backtest?

**Minimum:** 2 years

**Recommended:** 3-5 years to include:
- Bull markets
- Bear markets
- Sideways markets
- High volatility events

### Can backtests guarantee profits?

**No. Backtesting limitations:**
- Past performance ≠ future results
- Can't predict black swan events
- May overfit to historical data
- Doesn't account for all costs
- Liquidity assumptions may be wrong

**Use backtesting to:**
- Eliminate bad strategies
- Compare approaches
- Build confidence
- Identify risks

### How accurate are backtests?

**Factors affecting accuracy:**
- ✅ Uses real historical prices
- ✅ Includes stop-losses
- ✅ No lookahead bias
- ⚠️ Simplified slippage model
- ⚠️ Assumes perfect fills
- ⚠️ No market impact

**Expect live performance 20-30% worse than backtest.**

---

## Configuration

### Where is configuration stored?

**Two places:**

1. **`.env` file** (persistent):
   ```bash
   STRATEGY=momentum
   LOOKBACK_DAYS=20
   AUTO_TRADE=true
   ```

2. **API/UI updates** (in-memory, lost on restart):
   ```bash
   curl -X POST /api/config -d '{"momentum_threshold": 0.03}'
   ```

### Can I save configuration changes?

**Currently:** API/UI changes are temporary (reset on restart)

**Workaround:** Manually update `.env` file

**Future:** Configuration persistence (Phase 8 in roadmap)

### What's the difference between paper and live mode?

**Paper Trading** (`TRADING_MODE=paper`):
- Uses real market data
- Simulated order execution
- No real money
- Same API as live
- Perfect for testing

**Live Trading** (`TRADING_MODE=live`):
- Real market data
- Real order execution
- **Real money at risk**
- Requires explicit opt-in

### How do I switch from paper to live?

1. **Test thoroughly in paper mode** (30-90 days)
2. **Verify strategy performance**
3. **Set conservative limits:**
   ```bash
   MAX_POSITION_PCT=0.10  # 10% positions
   STOP_LOSS_PCT=0.03     # 3% stop loss
   MAX_DAILY_TRADES=2     # Limit trades
   ```
4. **Update `.env`:**
   ```bash
   TRADING_MODE=live
   ALPACA_API_KEY=your_live_key
   ALPACA_SECRET_KEY=your_live_secret
   ```
5. **Restart bot**
6. **Start with small capital**
7. **Monitor closely**

---

## Technical

### What technology does it use?

- **Language:** Python 3.10+
- **Web Framework:** FastAPI
- **Broker API:** alpaca-trade-api
- **Data Analysis:** pandas, numpy
- **Async:** asyncio
- **WebSocket:** Built into FastAPI

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

### Does it support other brokers?

**Currently:** Alpaca only

**Future:** Interactive Brokers, TD Ameritrade (Phase 6)

**Workaround:** Adapt `broker.py` for your broker's API

### Can I run multiple bots?

**Yes, but carefully:**

```bash
# Bot 1 (Momentum)
API_PORT=8000 STRATEGY=momentum python server.py

# Bot 2 (Mean Reversion)
API_PORT=8001 STRATEGY=mean_reversion python server.py
```

**Considerations:**
- Use different API ports
- Share the same Alpaca account
- Bots might conflict (buy/sell same stock)
- Better to use single bot with diversified watchlist

### What are system requirements?

**Minimum:**
- 1 CPU core
- 512MB RAM
- 1GB disk space
- Internet connection

**Recommended:**
- 2 CPU cores
- 2GB RAM
- 5GB disk (for historical data)
- Stable internet

### Can I run it on a Raspberry Pi?

**Yes!** Market-Watch works on Raspberry Pi 4:

```bash
# Install Python 3.10
sudo apt update
sudo apt install python3.10 python3.10-venv -y

# Follow standard setup
git clone ...
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

**Performance:** Sufficient for paper trading with small watchlists

---

## Troubleshooting

### Bot won't start

**Check:**
1. **Python version:** `python --version` (need 3.10+)
2. **Dependencies:** `pip install -r requirements.txt`
3. **API keys:** Verify in `.env` file
4. **Port availability:** Check port 8000 not in use
5. **Logs:** Look for error messages

### No trades executing

**Possible causes:**

1. **Auto-trade disabled:**
   ```bash
   AUTO_TRADE=true  # in .env
   ```

2. **Market closed:**
   - Bot only trades during market hours (9:30am-4pm ET)

3. **No signals:**
   - Check `/api/status` → signals
   - Adjust thresholds if too strict

4. **Risk limits:**
   - Insufficient buying power
   - Daily trade limit reached
   - Position size too small

5. **Check logs** for errors

### Bot crashes or restarts

**Common causes:**

1. **API errors:**
   - Alpaca API down (check status.alpaca.markets)
   - Rate limit exceeded
   - Invalid API keys

2. **Memory issues:**
   - Too many symbols in watchlist
   - Large lookback period
   - Solution: Reduce watchlist or lookback

3. **Network issues:**
   - Lost internet connection
   - Firewall blocking API calls

**Enable auto-restart** with systemd (see DEPLOYMENT.md)

### Signals not updating

1. **Check data fetch interval:**
   ```bash
   TRADE_INTERVAL_MINUTES=5  # Set to reasonable value
   ```

2. **Trigger manual refresh:**
   ```bash
   curl -X POST http://localhost:8000/api/bot/refresh
   ```

3. **Check market hours** (bot pauses when closed)

4. **Restart bot** if stuck

### WebSocket not connecting

1. **Check URL:** `ws://localhost:8000/ws` (not `wss://` for local)
2. **CORS settings:** Check `ALLOWED_ORIGINS` in `.env`
3. **Browser console:** Look for errors
4. **Firewall:** Ensure port 8000 accessible

### Historical data download fails

**Possible issues:**

1. **API limits:** Alpaca limits historical data requests
   - Wait 1 minute between downloads
   - Use `--force` flag carefully

2. **Invalid date range:**
   - Start date too old (Alpaca has limits)
   - End date in future

3. **Symbol doesn't exist:**
   - Check ticker symbol spelling
   - Some stocks have limited history

**Solution:**
```bash
# Download in smaller batches
python -m backtest --download --symbols AAPL,GOOGL --start 2022-01-01
# Wait 1 minute
python -m backtest --download --symbols MSFT,NVDA --start 2022-01-01
```

---

## Safety & Risk

### Is my money safe?

**Security measures:**
- API keys stored locally (never transmitted to us)
- Direct connection to Alpaca (no intermediaries)
- Open source (you can audit code)

**Your responsibility:**
- Secure your API keys
- Test in paper mode first
- Use strong passwords
- Enable 2FA on Alpaca account

### What are the risks?

**Technical risks:**
- Bot crashes (positions remain open)
- Internet outage (no stop-losses enforced)
- API errors (trades may fail)
- Bugs in code

**Trading risks:**
- Strategy may lose money
- Unexpected market events
- Slippage and liquidity issues
- Overnight gaps (holdings at risk)

**Mitigation:**
- Start with paper trading
- Use conservative position sizes
- Set tight stop-losses
- Monitor regularly
- Have exit strategy

### Can the bot lose all my money?

**Theoretically yes, if:**
- Multiple positions gap down overnight
- No stop-losses set
- Over-leveraged
- Black swan event

**Protection:**
- Set `STOP_LOSS_PCT` (default 5%)
- Use `MAX_POSITION_PCT` (default 25%)
- Set `MAX_DAILY_TRADES` limit
- Don't use all capital
- Monitor daily

### Should I run this with real money?

**Only if:**
- ✅ Tested 30+ days in paper mode
- ✅ Backtested strategy extensively
- ✅ Understand how it works
- ✅ Can afford to lose the money
- ✅ Have risk management in place
- ✅ Monitor it regularly

**Don't if:**
- ❌ New to trading
- ❌ Can't afford losses
- ❌ Don't understand the strategy
- ❌ Expecting guaranteed returns
- ❌ Won't monitor it

### How do I limit losses?

1. **Stop-loss:**
   ```bash
   STOP_LOSS_PCT=0.03  # 3% max loss per position
   ```

2. **Position sizing:**
   ```bash
   MAX_POSITION_PCT=0.10  # Only 10% per position
   ```

3. **Daily limits:**
   ```bash
   MAX_DAILY_TRADES=2  # Limit activity
   ```

4. **Account size:**
   - Only deposit what you can afford to lose

5. **Monitoring:**
   - Check daily
   - Set alerts for large losses
   - Have manual stop plan

---

## Still Have Questions?

- **Documentation:** Check [docs/](.) folder
- **Issues:** [GitHub Issues](https://github.com/yourusername/market-watch/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/market-watch/discussions)

---

*Last updated: 2025-01-19*
