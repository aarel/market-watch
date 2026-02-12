# market-watch Reality Check & Limitations

**Document Purpose**: Honest assessment of what market-watch IS and ISN'T, addressing common misconceptions about algorithmic trading and setting realistic expectations.

**Last Updated**: 2026-02-10

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [The Six Major Trading Risks](#the-six-major-trading-risks)
3. [How market-watch Addresses Each Risk](#how-market-watch-addresses-each-risk)
4. [What market-watch IS and ISN'T](#what-market-watch-is-and-isnt)
5. [Realistic Performance Expectations](#realistic-performance-expectations)
6. [Recommendations for Success](#recommendations-for-success)
7. [Future Development Priorities](#future-development-priorities)
8. [market-gambler Concept (High-Risk Alternative)](#market-gambler-concept)

---

## Executive Summary

**market-watch is a systematic momentum trading framework designed to:**
- Remove emotional decision-making from trading
- Apply consistent risk management
- Automate trade execution and monitoring
- Provide a learning platform for algorithmic trading

**market-watch is NOT:**
- A guaranteed money-making system
- A replacement for professional traders
- A "get rich quick" solution
- A tax-optimized investment vehicle
- A high-frequency day trading bot

**Realistic Outcome**: 5-12% annual returns after taxes, with 10-20% drawdowns, comparable to passive index investing but requiring active system maintenance.

---

## The Six Major Trading Risks

These are the core reasons why **60-70% of retail traders lose money**:

### 1. Inherent Market Difficulty
- Zero-sum game: For every winner, there's a loser
- Competing against professionals with better resources
- No strategy wins consistently forever
- Market conditions change, strategies degrade

### 2. Transaction Costs
- Bid-ask spread slippage (1-10 cents per trade)
- Price impact (large orders move market against you)
- Opportunity cost (capital locked in positions)
- Even "commission-free" has hidden costs

### 3. Constant Monitoring Required
- Markets move 9:30am-4pm ET, 5 days/week
- Need to watch positions for stop losses
- Manual intervention needed for system issues
- Psychological drain of constant vigilance

### 4. Psychological Stress
- Anxiety watching account value fluctuate
- Temptation to override system during losses
- Fear during drawdowns (10-20% drops)
- Responsibility for configuration decisions

### 5. Pattern Day Trader (PDT) Rule
- **Rule**: 4+ day trades in 5 days requires $25k minimum
- **Day trade**: Buy and sell same stock same day
- **Penalty**: Account frozen for 90 days if violated
- **Impact**: Limits small accounts (<$25k) to 3 day trades/week

### 6. Tax Implications
- Every trade is a taxable event
- Short-term gains (<1 year hold) = ordinary income rates (10-37%)
- Long-term gains (>1 year hold) = lower rates (0-20%)
- 200 trades/year = 200 tax events to track
- No tax optimization in strategy

---

## How market-watch Addresses Each Risk

### Risk 1: Market Difficulty
**Status**: ⚠️ **PARTIALLY MITIGATED** (Grade: C+)

**What market-watch does:**
- ✅ **Risk management**: Position sizing, stop losses, circuit breakers
- ✅ **Systematic approach**: Removes emotion, consistent execution
- ✅ **Momentum strategy**: Follows proven technical edge
- ✅ **Diversification**: 5-15 positions across sectors
- ✅ **Backtesting**: Test strategies before risking capital

**What it DOESN'T solve:**
- ❌ Market is still zero-sum - you're trading against professionals
- ❌ No strategy guarantees profits
- ❌ Past performance ≠ future results
- ❌ Competing with algorithms that cost millions to develop

**Impact**: Better odds than random/emotional trading, but **not guaranteed profits**.

---

### Risk 2: Transaction Costs
**Status**: ✅ **MOSTLY ADDRESSED** (Grade: B+)

**What market-watch does:**
- ✅ **Low trade frequency**: 1-10 trades/day (not 100+)
- ✅ **Limit orders**: Better fills than market orders
- ✅ **Position minimums**: Avoid tiny, cost-inefficient trades
- ✅ **Alpaca broker**: Commission-free stock trading

**What it DOESN'T solve:**
- ⚠️ **Bid-ask spread**: 1-10 cents lost per trade (0.1-0.3% slippage)
- ⚠️ **Price impact**: Large orders can move the market
- ⚠️ **Opportunity cost**: Capital tied up in positions

**Cost Analysis:**
```
Configuration: 5 trades/day, 250 trading days/year
Annual trades: ~1,250
Average slippage: 0.15% per round-trip
Annual cost: 0.15% × 1,250 = 0.375% of capital

On $100k account: ~$375/year in implicit costs
vs. Day trading (500 trades/day): ~$18,750/year (50x more!)
```

**Impact**: Much better than day trading, but costs are real and reduce returns.

---

### Risk 3: Constant Monitoring
**Status**: ✅ **MOSTLY SOLVED** (Grade: A)

**What market-watch does:**
- ✅ **Fully automated**: Runs 24/7 without human intervention
- ✅ **Auto-execution**: Trades execute automatically
- ✅ **Auto-monitoring**: Stop losses and targets tracked
- ✅ **Circuit breakers**: Prevent runaway losses
- ✅ **Alerts**: Email/webhook notifications for critical events

**What you still need to monitor:**
- ⚠️ **System uptime**: Server crashes, network issues
- ⚠️ **Broker API health**: Alpaca outages do happen
- ⚠️ **Strategy performance**: Weekly review recommended
- ⚠️ **Configuration**: Ensure settings haven't drifted

**Time Investment:**
- Daily: 0 minutes (unless alerts fire)
- Weekly: 15-30 minutes (health check, performance review)
- Monthly: 1-2 hours (deep dive, strategy evaluation)

**Impact**: 95% hands-off. You can walk away for days, but weekly check-ins recommended.

---

### Risk 4: Psychological Stress
**Status**: ✅ **SIGNIFICANTLY REDUCED** (Grade: B)

**What market-watch does:**
- ✅ **Removes emotional decisions**: No panic selling, no FOMO buying
- ✅ **Predefined rules**: Strategy executes consistently
- ✅ **Automatic stop losses**: Can't hold losers hoping for recovery
- ✅ **No need to watch tickers**: Bot handles everything

**What it DOESN'T eliminate:**
- ⚠️ **Anxiety watching account**: Still stressful to see -10% drawdowns
- ⚠️ **Temptation to intervene**: "Should I override the bot?"
- ⚠️ **Responsibility**: You configured it, you're accountable for losses
- ⚠️ **Fear during bad periods**: 10-20% drops WILL happen

**Stress Comparison:**
```
Manual trading stress:     ██████████ 10/10 (constant vigilance)
market-watch stress:       ██░░░░░░░░  2/10 (weekly check-ins)
Passive index investing:   █░░░░░░░░░  1/10 (quarterly review)
```

**Impact**: 80% stress reduction vs. manual trading, but drawdowns are still emotionally challenging.

---

### Risk 5: Pattern Day Trader (PDT) Rule
**Status**: ⚠️ **PARTIALLY ADDRESSED** (Grade: C)

**PDT Rule Explained:**
- **Trigger**: 4+ day trades in 5 rolling business days
- **Day trade**: Buy and sell same stock same day
- **Requirement**: $25k minimum equity
- **Penalty**: Account restricted to closing trades only for 90 days

**How market-watch handles it:**
- ✅ **Swing trading style**: Default holds positions days/weeks (not intraday)
- ✅ **Lower frequency**: 1-10 trades/day reduces day trade risk
- ✅ **Most trades NOT day trades**: Buy Monday, sell Wednesday = safe

**What it DOESN'T solve:**
- ⚠️ **Some trades WILL be day trades**: Stop losses can trigger same-day
- ⚠️ **Tight stops increase risk**: 1% stop loss = more intraday exits
- ❌ **No PDT tracking built-in**: System doesn't count day trades
- ❌ **No warnings**: Won't alert you before 4th day trade

**Risk Analysis with Current Settings:**
```
Stop loss: 1%
Sell threshold: -1%
Volatility: High
Trade frequency: ~5/day

Estimated day trades per week: 2-5
Risk of PDT flag: MODERATE (if account < $25k)
```

**Recommendations:**
- **If account < $25k**: Loosen stop loss to 3-5% (reduces day trades)
- **Manual tracking**: Keep count of day trades in rolling 5-day window
- **Conservative approach**: Limit to 2 day trades/week maximum

**Impact**: Usually not an issue with default settings, but **high risk with tight stops and small accounts**.

---

### Risk 6: Tax Implications
**Status**: ❌ **NOT ADDRESSED** (Grade: F)

**The Tax Reality:**
- Every trade = taxable event (even in PAPER mode planning for LIVE)
- Short-term gains (<1 year hold) = ordinary income (10-37% federal + state)
- Long-term gains (>1 year hold) = preferential rates (0-20%)
- market-watch holds days/weeks = **100% short-term gains**

**What market-watch does:**
- ✅ **Logs all trades**: Helpful for tax reporting (CSV export)
- ✅ **Analytics track P&L**: Easy to see gross profit
- ✅ **Trade history**: Detailed records

**What it DOESN'T do:**
- ❌ **No tax optimization**: Doesn't consider tax implications
- ❌ **No tax-loss harvesting**: Doesn't strategically realize losses
- ❌ **No holding period optimization**: Doesn't favor long-term gains
- ❌ **No wash sale tracking**: Can't warn about wash sale violations

**Tax Impact Example:**
```
Scenario: $100k account, 200 trades/year, 55% win rate
-----------------------------------------------------
Gross profit: 110 wins × $100 avg = $11,000
Tax rate (37% bracket):            -$4,070
Net profit after tax:               $6,930

Effective return: 11% gross → 6.93% net
```

**Comparison to Buy-and-Hold:**
```
Strategy          | Gross Return | Tax Rate | Net Return | Trades/Year
-----------------------------------------------------------------------
market-watch      | 10%          | 37%      | 6.3%       | 200
Index fund (1yr+) | 10%          | 20%      | 8.0%       | 1
                  |              |          | +27% better|
```

**Impact**: **Taxes take 30-40% of profits** in high brackets. A major hidden cost that significantly reduces returns compared to buy-and-hold.

**Mitigation Ideas for Future:**
- Track holding periods, favor positions approaching 1 year
- Tax-loss harvesting: Realize losses to offset gains
- Wash sale awareness: Don't rebuy same stock within 30 days
- Consider tax-advantaged accounts (IRA/401k, but limits apply)

---

## What market-watch IS and ISN'T

### ✅ market-watch IS:

1. **A Systematic Trading Framework**
   - Codifies trading rules into executable logic
   - Removes discretionary decisions
   - Consistent execution across all conditions

2. **A Risk Management System**
   - Position sizing based on account value
   - Stop losses to limit downside
   - Circuit breakers for catastrophic scenarios
   - Diversification across positions

3. **An Automation Tool**
   - Removes emotion from trading
   - Executes 24/7 without fatigue
   - Monitors positions continuously
   - Responds faster than humans

4. **A Learning Platform**
   - Teaches algorithmic trading concepts
   - Event-driven architecture
   - Modular design for experimentation
   - Real-time observability

5. **Better Than Random/Emotional Trading**
   - Consistent rules > gut feelings
   - Risk management > YOLO trades
   - Backtestable > guesswork
   - Data-driven > hope-driven

### ❌ market-watch is NOT:

1. **A Guaranteed Money Printer**
   - Will have losing periods (10-20% drawdowns)
   - Strategies degrade over time
   - Market conditions change
   - No "holy grail" algorithm exists

2. **Tax-Optimized**
   - All short-term gains (highest tax rates)
   - No consideration of holding periods
   - No tax-loss harvesting
   - 200 trades = 200 taxable events/year

3. **Foolproof**
   - Can have bugs
   - Broker API can fail
   - Strategies can stop working
   - Black swan events happen

4. **PDT-Aware**
   - Doesn't track day trades
   - Can violate PDT rule with tight stops
   - Requires manual monitoring if account < $25k

5. **Competitive with Professionals**
   - Hedge funds have better data
   - Market makers have faster systems
   - Institutions have more capital
   - Professionals have teams of PhDs

6. **Passive Income**
   - Requires weekly monitoring
   - System maintenance needed
   - Strategy tuning over time
   - Can't truly "set and forget"

---

## Realistic Performance Expectations

### Best Case Scenario
```
Annual return:        12-15% (before taxes)
After-tax return:     8-10% (37% bracket)
Win rate:             60-65%
Max drawdown:         -15%
Time investment:      1-2 hours/week
Trades per year:      150-300
```

### Likely Scenario
```
Annual return:        8-12% (before taxes)
After-tax return:     5-8% (37% bracket)
Win rate:             55-60%
Max drawdown:         -20%
Time investment:      2-4 hours/week
Trades per year:      200-400
```

### Worst Case Scenario (but still trading)
```
Annual return:        0-5% (before taxes)
After-tax return:     0-3% (37% bracket)
Win rate:             50-55%
Max drawdown:         -30%
Time investment:      4-8 hours/week (troubleshooting)
Trades per year:      300-500
```

### Reality Check: Comparison to Alternatives

| Strategy               | Annual Return | Risk | Time/Week | Skill Required |
|------------------------|---------------|------|-----------|----------------|
| market-watch           | 5-10%*        | Med  | 1-2 hrs   | Medium         |
| S&P 500 Index Fund     | 10%**         | Med  | 0 hrs     | None           |
| Professional Day Trader| 10-30%        | High | 60+ hrs   | Very High      |
| Random Stock Picking   | -5 to 5%      | High | 5-10 hrs  | None           |
| Savings Account        | 0.5-2%        | None | 0 hrs     | None           |

*After taxes
**Historical average, before taxes

**Key Insight**: market-watch returns are **comparable to index funds** but with:
- More complexity
- More time required
- More stress
- Worse tax treatment

**The honest question**: Why not just buy SPY and hold?

**Valid reasons to use market-watch:**
1. Learning algorithmic trading (education value)
2. Enjoying the challenge (hobby/entertainment)
3. Building skills for future career (resume value)
4. Testing strategies before scaling (R&D)

**Invalid reasons:**
1. "Make money fast" (won't happen)
2. "Beat the market easily" (you won't)
3. "Passive income" (requires active management)
4. "Get rich" (unlikely)

---

## Recommendations for Success

### Phase 0: Education (0-3 months)
**Goal**: Understand what you're getting into

- [ ] Read this entire document
- [ ] Study the codebase (`ROADMAP.md`, `ARCHITECTURE.md`)
- [ ] Learn basic trading concepts (momentum, stop loss, etc.)
- [ ] Understand risk management principles
- [ ] Research tax implications in your jurisdiction
- [ ] Set realistic expectations (5-10% annual, not 100%)

### Phase 1: Paper Trading (3-6 months)
**Goal**: Prove the strategy works before risking real money

- [ ] Run market-watch in PAPER mode only
- [ ] Track key metrics:
  - Total return (%)
  - Win rate (%)
  - Average win vs. average loss
  - Max drawdown (%)
  - Sharpe ratio
- [ ] Document all issues encountered
- [ ] Tune configuration based on results
- [ ] Achieve 3+ months of consecutive profitability
- [ ] **DO NOT GO LIVE UNTIL PAPER IS PROFITABLE**

### Phase 2: Small Capital Live (6-12 months)
**Goal**: Validate strategy with real money, minimize risk

- [ ] Start with $5k-$10k only (money you can afford to lose)
- [ ] Use same configuration that worked in paper
- [ ] Run in PAPER and LIVE simultaneously (compare performance)
- [ ] Monitor closely (daily check-ins first 2 weeks)
- [ ] Expect slippage (live results slightly worse than paper)
- [ ] Track actual costs (slippage, spreads)
- [ ] Document differences from paper trading

### Phase 3: Scale (12+ months)
**Goal**: Increase capital only after proving success

- [ ] Only scale if live trading is profitable for 6+ months
- [ ] Increase capital gradually (double account size at most)
- [ ] Watch for strategy degradation (larger orders = more slippage)
- [ ] Consider tax implications (quarterly estimated taxes)
- [ ] Maintain paper trading for strategy testing
- [ ] Never risk more than 20% of net worth

### Ongoing Maintenance

**Weekly Tasks** (15-30 min):
- Check system uptime and health (`./scripts/quick_status.sh`)
- Review open positions and P&L
- Verify no broker API issues
- Scan alerts for anomalies

**Monthly Tasks** (1-2 hours):
- Deep dive on strategy performance
- Review trade history and outcomes
- Check for configuration drift
- Update strategy if market conditions changed
- Reconcile with broker statements

**Quarterly Tasks** (2-4 hours):
- Backtest current strategy on recent data
- Compare live results to paper trading
- Evaluate new strategy ideas
- Tax planning (estimated taxes if needed)
- Review risk limits and position sizing

**Annual Tasks** (4-8 hours):
- Full year performance analysis
- Tax preparation (1099s, Schedule D)
- Strategy evaluation and major changes
- Infrastructure upgrades
- Review goals and expectations

### Red Flags to Stop Trading

**Immediately pause and investigate if:**
- Account down >15% in a week
- Win rate drops below 50% for a month
- System crashes repeatedly
- Broker API issues persist
- Strange trades you don't understand
- Drawdown exceeds max acceptable loss
- Personal stress becomes overwhelming

**Never:**
- Trade money you can't afford to lose
- Assume past performance = future results
- Ignore warning signs because "it'll recover"
- Increase position sizes after losses (revenge trading)
- Turn off risk limits to "let it run"
- Stop monitoring because "it's automated"

---

## Future Development Priorities

Based on the reality check above, here are recommended improvements:

### Priority 1: Risk Management Enhancements
**Addresses**: Market difficulty, psychological stress

- [ ] **Improved position sizing** - Kelly criterion, volatility-adjusted
- [ ] **Dynamic stop losses** - ATR-based, tighten as profit grows
- [ ] **Correlation tracking** - Avoid overconcentration in same sector
- [ ] **Volatility regime detection** - Reduce size in high-vol markets
- [ ] **Drawdown protection** - Reduce exposure after losing streaks

### Priority 2: PDT Tracking & Compliance
**Addresses**: PDT rule violations

- [ ] **Day trade counter** - Track rolling 5-day window
- [ ] **PDT warnings** - Alert before 4th day trade
- [ ] **Account size check** - Enforce $25k minimum for day trading mode
- [ ] **Forced swing mode** - Disable day trades if account < $25k
- [ ] **Trade delay** - Minimum hold time to avoid day trades

### Priority 3: Cost Reduction
**Addresses**: Transaction costs

- [ ] **Slippage tracking** - Measure actual costs per trade
- [ ] **Trade frequency optimization** - Find sweet spot for costs vs. performance
- [ ] **Position size minimums** - Ensure costs don't eat profits
- [ ] **Limit order improvement** - Better price optimization
- [ ] **Batch trading** - Combine small orders

### Priority 4: Tax Optimization
**Addresses**: Tax implications (currently F grade)

- [ ] **Holding period tracking** - Know when positions hit 1 year (long-term)
- [ ] **Tax-loss harvesting** - Strategically realize losses to offset gains
- [ ] **Wash sale detection** - Warn when rebuy would violate wash sale rule
- [ ] **Tax reporting** - Auto-generate Schedule D-ready CSV
- [ ] **Tax-aware exits** - Prefer selling positions approaching long-term status

### Priority 5: Strategy Improvements
**Addresses**: Market difficulty, performance

- [ ] **Strategy diversification** - Run multiple strategies simultaneously
- [ ] **Regime detection** - Switch strategies based on market conditions
- [ ] **Machine learning** - Adaptive parameter tuning
- [ ] **Sentiment analysis** - Incorporate news/social signals
- [ ] **Options strategies** - Covered calls for income, protective puts

### Priority 6: System Reliability
**Addresses**: Constant monitoring requirement

- [ ] **Failover system** - Backup server for high availability
- [ ] **Health monitoring** - Auto-restart on crashes
- [ ] **Broker redundancy** - Multi-broker support
- [ ] **Alert improvements** - SMS, push notifications
- [ ] **Audit logging** - Full trail for debugging

### Priority 7: User Experience
**Addresses**: Psychological stress, monitoring burden

- [ ] **Mobile app** - Check status on the go
- [ ] **Better visualizations** - Intuitive performance charts
- [ ] **Simplified configuration** - Profiles for conservative/moderate/aggressive
- [ ] **Onboarding wizard** - Step-by-step setup
- [ ] **Explainability** - "Why did the bot do that?" feature

### Non-Priorities (Not Worth Building)
- ❌ **High-frequency trading** - Can't compete with professionals
- ❌ **News scraping** - Slow and unreliable
- ❌ **Social media sentiment** - Noisy and manipulated
- ❌ **Complex ML models** - Overfit easily, degrade quickly
- ❌ **Cryptocurrency** - Too volatile, different risk profile

---

## market-gambler Concept (High-Risk Alternative)

For users who understand the risks and want more active trading:

### Concept Summary
**market-gambler**: A high-frequency, high-risk day trading bot for users who:
- Understand they'll likely lose money
- Want to learn about scalping/day trading
- Have $25k+ account (PDT compliant)
- Can accept 50%+ annual volatility
- Treat it as gambling, not investing

### Key Differences from market-watch

| Feature | market-watch | market-gambler |
|---------|--------------|----------------|
| **Philosophy** | Risk-managed swing trading | High-risk scalping |
| **Holding period** | Days to weeks | Minutes to hours |
| **Trades/day** | 1-10 | 50-500 |
| **Position size** | 5-15% per trade | 25-50% per trade |
| **Stop loss** | 1-3% | 0.2-0.5% |
| **Profit target** | 5-20% | 0.5-2% |
| **Leverage** | 1x (no margin) | 2x-4x |
| **Win rate target** | 60-70% | 50-55% |
| **Annual return goal** | 8-12% | 20-50% (or -30%) |
| **Risk of ruin** | Low | **HIGH** |

### Architecture (95% Reusable from market-watch)

**Keep from market-watch:**
- ✅ EventBus (event-driven core)
- ✅ BaseAgent (agent framework)
- ✅ AlpacaBroker (broker abstraction)
- ✅ Universe system (PAPER/LIVE isolation)
- ✅ ConfigManager
- ✅ ObservabilityAgent
- ✅ AnalyticsAgent
- ✅ Server/API (FastAPI)
- ✅ UI framework

**Build new for market-gambler:**
- 🆕 ScalpingStrategy (1-5 min bars, VWAP, RSI)
- 🆕 RapidRiskAgent (fast checks, <100ms)
- 🆕 FastExecutionAgent (market orders only)
- 🆕 ScalpMonitorAgent (check every 10 seconds)
- 🆕 AggressivePositionSizer (25-50% per trade)
- 🆕 EODCloser (force close all at 3:59pm)

### Code Reuse Estimate
- 90% infrastructure reusable
- 10% new strategy/risk code
- Could build in 1-2 weeks

### Reality Check on market-gambler

**Expected outcomes:**
- 70% chance: Lose 10-30% in first year
- 20% chance: Break even (after costs)
- 10% chance: Profit 20-50%

**Why it will probably fail:**
- Transaction costs eat profits (0.15% × 500 trades/day = 75% annual)
- Slippage on market orders (worse fills)
- Competing with professional scalpers
- Psychological stress (wins/losses every minute)
- More chances for bugs to cost money

**Valid reasons to build it:**
- Learning experience (educational value)
- Research project (study HFT concepts)
- Proof you can't beat professionals (valuable lesson)

**Invalid reasons:**
- "I'll get rich quick" (you won't)
- "It's just like a video game" (it's your real money)

### Recommendation
**DON'T BUILD market-gambler unless:**
1. market-watch is profitable for 6+ months in PAPER
2. You have $50k+ to gamble (beyond emergency fund)
3. You understand 70% chance of loss
4. You can afford to lose it all
5. It's for education, not income

**Better alternative:**
- Use market-watch with tighter stops (1%)
- Increase trade frequency slightly (20-30/day)
- Still much safer than true day trading
- Might satisfy the "action" craving without the risk

---

## Conclusion

**market-watch is a well-designed algorithmic trading framework** that addresses most of the common pitfalls of retail trading. However, it is NOT a guaranteed path to wealth.

**Realistic assessment:**
- ✅ Better than emotional/random trading
- ✅ Comparable to index fund returns (5-10% after tax)
- ✅ Good learning platform for algo trading
- ⚠️ Requires ongoing maintenance (not passive)
- ⚠️ Tax treatment is poor (short-term gains)
- ❌ Won't make you rich quickly
- ❌ Still carries significant risk

**The honest answer:**
If your goal is **long-term wealth**, buying and holding SPY might be better (10% return, minimal taxes, zero effort).

If your goal is **learning algorithmic trading** or you **enjoy the challenge**, market-watch is excellent.

If your goal is **making money fast**, neither market-watch nor market-gambler will deliver. That's not how markets work.

**Set realistic expectations, start in PAPER mode, and prove it works before risking real capital.**

---

**Document Version**: 1.0
**Last Updated**: 2026-02-10
**Next Review**: Quarterly (2026-05-10)

