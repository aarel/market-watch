"""Paper Trading Insights engine.

Pure functions only — no file I/O, no side effects.

Synthesises enriched paper trade records into structured, human-readable
insights across five categories:
  signal_quality   — which signal reasons / strengths correlate with wins
  timing           — market-open vs closed execution, best trading hours
  symbol_performance — best/worst symbols by realised P&L
  risk             — loss severity, stop-loss headroom
  portfolio        — equity trajectory, win-rate trend

Each insight degrades gracefully: if fewer than MIN_SAMPLES data points are
available for a computation, that insight is omitted rather than misleading.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Minimum observations required to emit a statistic. Below this threshold
# the sample size is too small to draw meaningful conclusions.
MIN_SAMPLES = 3


@dataclass
class Insight:
    """A single synthesised observation about the paper trading history."""
    category: str          # "signal_quality" | "timing" | "symbol_performance" | "risk" | "portfolio"
    headline: str          # ≤80 chars — scan-able summary
    detail: str            # 1-2 sentences elaborating on the headline
    value: float | None    # primary numeric supporting the headline (or None)
    direction: str         # "positive" | "negative" | "neutral"


def compute_insights(
    trades: list[dict],
    equity: list[dict] | None = None,
) -> list[Insight]:
    """Compute all available insights from paper trade and equity history.

    Args:
        trades: Trade records from AnalyticsStore.load_trades(), optionally
            enriched with perf_1d/5d/10d fields and signal/market context.
        equity: Optional equity snapshots from AnalyticsStore.load_equity().

    Returns:
        List of Insight objects, ordered by category then descending |value|.
        Insights are omitted when there are fewer than MIN_SAMPLES observations.
    """
    from analytics.metrics import compute_round_trip_trades

    pairs = compute_round_trip_trades(trades)
    insights: list[Insight] = []

    insights.extend(_signal_quality_insights(trades, pairs))
    insights.extend(_timing_insights(trades, pairs))
    insights.extend(_symbol_performance_insights(pairs))
    insights.extend(_risk_insights(pairs))
    if equity:
        insights.extend(_portfolio_insights(equity, pairs))

    return insights


# ---------------------------------------------------------------------------
# Signal quality
# ---------------------------------------------------------------------------

def _signal_quality_insights(trades: list[dict], pairs: list[dict]) -> list[Insight]:
    insights: list[Insight] = []

    # 1. Overall win rate from round trips
    if len(pairs) >= MIN_SAMPLES:
        wins = sum(1 for p in pairs if float(p.get("pnl") or 0) > 0)
        win_rate = wins / len(pairs) * 100
        direction = "positive" if win_rate >= 55 else ("negative" if win_rate < 45 else "neutral")
        insights.append(Insight(
            category="signal_quality",
            headline=f"Overall win rate: {win_rate:.0f}% across {len(pairs)} completed trades",
            detail=(
                f"{wins} of {len(pairs)} round-trip trades closed profitable. "
                f"{'Above' if win_rate >= 55 else 'Below' if win_rate < 45 else 'At'} the "
                f"55% threshold typically needed to be consistently profitable with a 1:1 risk/reward."
            ),
            value=round(win_rate, 1),
            direction=direction,
        ))

    # 2. Win rate by signal reason
    reason_buckets: dict[str, list[float]] = {}
    for t in trades:
        reason = (t.get("signal_reason") or "").strip()
        if not reason:
            continue
        # Match this trade to a pair (same symbol, approximate time) — not
        # available directly, so use per-trade side and filled_avg_price
        # as a proxy: buys with a reason label the signal; we track their outcome
        # via pairs matched by symbol and approximate price.
        # Simpler proxy: use side=buy trades and see if same-symbol pair was a win.
    # Build symbol→pnl map from pairs for signal reason lookup
    symbol_pnl: dict[str, list[float]] = {}
    for p in pairs:
        sym = p.get("symbol", "")
        symbol_pnl.setdefault(sym, []).append(float(p.get("pnl") or 0))

    for t in trades:
        if t.get("side") != "buy":
            continue
        reason = (t.get("signal_reason") or "").strip()
        if not reason:
            continue
        sym = t.get("symbol", "")
        pnls = symbol_pnl.get(sym, [])
        if pnls:
            reason_buckets.setdefault(reason, []).append(pnls[0])

    for reason, pnls in reason_buckets.items():
        if len(pnls) < MIN_SAMPLES:
            continue
        wr = sum(1 for p in pnls if p > 0) / len(pnls) * 100
        direction = "positive" if wr >= 60 else ("negative" if wr < 40 else "neutral")
        label = reason[:40] + "…" if len(reason) > 40 else reason
        insights.append(Insight(
            category="signal_quality",
            headline=f"Signal '{label}': {wr:.0f}% win rate ({len(pnls)} trades)",
            detail=(
                f"Trades triggered by this signal reason had a {wr:.1f}% win rate. "
                f"{'Strong edge — consider raising allocation for this signal.' if wr >= 60 else 'Below baseline — review signal criteria.' if wr < 40 else 'Neutral performance — monitor over more trades.'}"
            ),
            value=round(wr, 1),
            direction=direction,
        ))

    # 3. Signal strength correlation
    strength_data: list[tuple[float, float]] = []  # (strength, pnl)
    for t in trades:
        if t.get("side") != "buy":
            continue
        strength = t.get("signal_strength")
        if strength is None:
            continue
        sym = t.get("symbol", "")
        pnls = symbol_pnl.get(sym, [])
        if pnls:
            strength_data.append((float(strength), pnls[0]))

    if len(strength_data) >= MIN_SAMPLES:
        high = [(s, p) for s, p in strength_data if s >= 0.7]
        low = [(s, p) for s, p in strength_data if s < 0.7]
        if len(high) >= MIN_SAMPLES and len(low) >= MIN_SAMPLES:
            high_wr = sum(1 for _, p in high if p > 0) / len(high) * 100
            low_wr = sum(1 for _, p in low if p > 0) / len(low) * 100
            diff = high_wr - low_wr
            direction = "positive" if diff > 5 else ("negative" if diff < -5 else "neutral")
            insights.append(Insight(
                category="signal_quality",
                headline=f"Strong signals (≥0.7) win {high_wr:.0f}% vs {low_wr:.0f}% for weak",
                detail=(
                    f"High-strength signals (≥0.7) have a {high_wr:.1f}% win rate vs "
                    f"{low_wr:.1f}% for weaker signals across {len(high)+len(low)} qualifying trades. "
                    f"{'Strength is a useful filter — consider a minimum threshold.' if diff > 5 else 'Signal strength does not clearly predict trade outcome in this period.'}"
                ),
                value=round(diff, 1),
                direction=direction,
            ))

    # 4. Forward performance after trades (perf_1d)
    perf1d = [
        float(t["perf_1d"]) for t in trades
        if t.get("perf_1d") is not None
    ]
    if len(perf1d) >= MIN_SAMPLES:
        avg = sum(perf1d) / len(perf1d) * 100
        direction = "positive" if avg > 0.1 else ("negative" if avg < -0.1 else "neutral")
        insights.append(Insight(
            category="signal_quality",
            headline=f"Portfolio gains {avg:+.2f}% on average 1 day after a trade",
            detail=(
                f"Measured across {len(perf1d)} trades, the portfolio equity changes "
                f"{avg:+.2f}% in the 24 hours following each trade. "
                f"{'Positive momentum — strategy is entering at good timing.' if avg > 0.1 else 'Portfolio typically declines after entries — review entry timing.' if avg < -0.1 else 'No consistent directional drift after entries.'}"
            ),
            value=round(avg, 3),
            direction=direction,
        ))

    return insights


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

def _timing_insights(trades: list[dict], pairs: list[dict]) -> list[Insight]:
    insights: list[Insight] = []

    # Market-open vs closed trade win rate (from market_context on buy trades)
    open_wins, open_total = 0, 0
    closed_wins, closed_total = 0, 0
    symbol_pnl: dict[str, list[float]] = {}
    for p in pairs:
        sym = p.get("symbol", "")
        symbol_pnl.setdefault(sym, []).append(float(p.get("pnl") or 0))

    for t in trades:
        if t.get("side") != "buy":
            continue
        ctx = t.get("market_context") or {}
        market_open = ctx.get("market_open")
        if market_open is None:
            continue
        sym = t.get("symbol", "")
        pnls = symbol_pnl.get(sym, [])
        if not pnls:
            continue
        is_win = pnls[0] > 0
        if market_open:
            open_total += 1
            if is_win:
                open_wins += 1
        else:
            closed_total += 1
            if is_win:
                closed_wins += 1

    if open_total >= MIN_SAMPLES and closed_total >= MIN_SAMPLES:
        open_wr = open_wins / open_total * 100
        closed_wr = closed_wins / closed_total * 100
        diff = open_wr - closed_wr
        direction = "positive" if abs(diff) > 5 else "neutral"
        better = "during market hours" if diff > 0 else "outside market hours"
        insights.append(Insight(
            category="timing",
            headline=f"Trades execute better {better} ({open_wr:.0f}% vs {closed_wr:.0f}% win rate)",
            detail=(
                f"Market-open trades: {open_wr:.1f}% win rate ({open_total} trades). "
                f"Pre/post-market trades: {closed_wr:.1f}% win rate ({closed_total} trades). "
                f"{'Consider restricting entries to regular trading hours.' if open_wr > closed_wr + 10 else 'Extended-hours entries may offer an edge — investigate further.' if closed_wr > open_wr + 10 else 'No strong timing advantage between market hours.'}"
            ),
            value=round(diff, 1),
            direction=direction,
        ))

    # High gainer count timing
    high_ctx = []
    low_ctx = []
    for t in trades:
        if t.get("side") != "buy":
            continue
        ctx = t.get("market_context") or {}
        count = ctx.get("top_gainer_count")
        if count is None:
            continue
        sym = t.get("symbol", "")
        pnls = symbol_pnl.get(sym, [])
        if not pnls:
            continue
        is_win = pnls[0] > 0
        if count >= 10:
            high_ctx.append(is_win)
        else:
            low_ctx.append(is_win)

    if len(high_ctx) >= MIN_SAMPLES and len(low_ctx) >= MIN_SAMPLES:
        high_wr = sum(high_ctx) / len(high_ctx) * 100
        low_wr = sum(low_ctx) / len(low_ctx) * 100
        diff = high_wr - low_wr
        direction = "positive" if diff > 5 else ("negative" if diff < -5 else "neutral")
        insights.append(Insight(
            category="timing",
            headline=f"High top-gainer days: {high_wr:.0f}% win rate vs {low_wr:.0f}% on quiet days",
            detail=(
                f"Days with ≥10 top gainers: {high_wr:.1f}% win rate ({len(high_ctx)} trades). "
                f"Quieter market days: {low_wr:.1f}% win rate ({len(low_ctx)} trades). "
                f"{'Momentum strategy works better on high-activity days.' if diff > 10 else 'Strategy performance does not strongly depend on market activity level.'}"
            ),
            value=round(diff, 1),
            direction=direction,
        ))

    return insights


# ---------------------------------------------------------------------------
# Symbol performance
# ---------------------------------------------------------------------------

def _symbol_performance_insights(pairs: list[dict]) -> list[Insight]:
    insights: list[Insight] = []
    if len(pairs) < MIN_SAMPLES:
        return insights

    by_symbol: dict[str, list[float]] = {}
    for p in pairs:
        sym = p.get("symbol") or "UNKNOWN"
        by_symbol.setdefault(sym, []).append(float(p.get("pnl") or 0))

    # Filter to symbols with enough trades
    qualified = {s: pnls for s, pnls in by_symbol.items() if len(pnls) >= MIN_SAMPLES}

    if qualified:
        # Best symbol by total P&L
        totals = {s: sum(ps) for s, ps in qualified.items()}
        best_sym = max(totals, key=lambda s: totals[s])
        best_total = totals[best_sym]
        direction = "positive" if best_total > 0 else "negative"
        insights.append(Insight(
            category="symbol_performance",
            headline=f"Best symbol: {best_sym} at ${best_total:,.2f} total P&L ({len(qualified[best_sym])} trades)",
            detail=(
                f"{best_sym} produced the highest cumulative P&L of ${best_total:,.2f} "
                f"across {len(qualified[best_sym])} completed round trips. "
                f"{'Consider reviewing allocation — this symbol is carrying the strategy.' if best_total > 0 else 'Even the best-performing symbol is down — review overall approach.'}"
            ),
            value=round(best_total, 2),
            direction=direction,
        ))

        # Worst symbol
        worst_sym = min(totals, key=lambda s: totals[s])
        worst_total = totals[worst_sym]
        if worst_sym != best_sym:
            direction = "negative" if worst_total < 0 else "positive"
            insights.append(Insight(
                category="symbol_performance",
                headline=f"Worst symbol: {worst_sym} at ${worst_total:,.2f} total P&L ({len(qualified[worst_sym])} trades)",
                detail=(
                    f"{worst_sym} had the lowest cumulative P&L at ${worst_total:,.2f} "
                    f"across {len(qualified[worst_sym])} round trips. "
                    f"{'Consider removing this symbol from the universe or tightening its risk limits.' if worst_total < 0 else 'All tracked symbols profitable — strategy shows broad effectiveness.'}"
                ),
                value=round(worst_total, 2),
                direction=direction,
            ))

    # Single-trade symbols summary
    single_trade_syms = [s for s, ps in by_symbol.items() if len(ps) == 1]
    if len(single_trade_syms) >= 3:
        single_pnls = [by_symbol[s][0] for s in single_trade_syms]
        single_total = sum(single_pnls)
        direction = "positive" if single_total > 0 else ("negative" if single_total < 0 else "neutral")
        insights.append(Insight(
            category="symbol_performance",
            headline=f"{len(single_trade_syms)} symbols traded only once — combined P&L ${single_total:,.2f}",
            detail=(
                f"These symbols each have only a single completed round trip, "
                f"so their win/loss statistics are not yet reliable. "
                f"More trades are needed before drawing conclusions about their individual performance."
            ),
            value=round(single_total, 2),
            direction=direction,
        ))

    return insights


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

def _risk_insights(pairs: list[dict]) -> list[Insight]:
    insights: list[Insight] = []
    if len(pairs) < MIN_SAMPLES:
        return insights

    pnls = [float(p.get("pnl") or 0) for p in pairs]
    losses = [p for p in pnls if p < 0]
    wins = [p for p in pnls if p > 0]

    # Average win vs average loss (expectancy)
    if len(wins) >= MIN_SAMPLES and len(losses) >= MIN_SAMPLES:
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
        direction = "positive" if ratio >= 1.5 else ("negative" if ratio < 1.0 else "neutral")
        insights.append(Insight(
            category="risk",
            headline=f"Avg win ${avg_win:.2f} vs avg loss ${avg_loss:.2f} — ratio {ratio:.2f}×",
            detail=(
                f"Average winning trade: +${avg_win:.2f}. Average losing trade: -${avg_loss:.2f}. "
                f"{'Healthy risk/reward — wins outpace losses per trade.' if ratio >= 1.5 else 'Losses outpace wins on average — need tighter stops or larger profit targets.' if ratio < 1.0 else 'Roughly 1:1 risk/reward — win rate needs to exceed 50% to be profitable.'}"
            ),
            value=round(ratio, 2),
            direction=direction,
        ))

    # Largest single loss
    if losses:
        worst = min(pnls)
        avg_win = abs(sum(wins) / len(wins)) if wins else 0
        direction = "negative" if (not wins or abs(worst) > avg_win * 2) else "neutral"
        insights.append(Insight(
            category="risk",
            headline=f"Largest single loss: ${worst:.2f}",
            detail=(
                f"The worst individual round-trip trade lost ${abs(worst):.2f}. "
                f"{'This loss is more than 2× the average winning trade — consider a hard stop-loss limit.' if wins and abs(worst) > sum(wins)/len(wins)*2 else 'Loss magnitude is within normal range relative to average wins.'}"
            ),
            value=round(worst, 2),
            direction="negative",
        ))

    # Consecutive losses check
    consecutive = _max_consecutive(pnls, predicate=lambda p: p < 0)
    if consecutive >= 3:
        direction = "negative" if consecutive >= 5 else "neutral"
        insights.append(Insight(
            category="risk",
            headline=f"Longest losing streak: {consecutive} consecutive trades",
            detail=(
                f"The strategy experienced {consecutive} consecutive losing round trips at one point. "
                f"{'Consider circuit-breaker rules to pause trading after extended drawdowns.' if consecutive >= 5 else 'A 3-4 trade streak is normal variance — monitor if it extends further.'}"
            ),
            value=float(consecutive),
            direction=direction,
        ))

    return insights


def _max_consecutive(values: list[float], predicate) -> int:
    """Return the length of the longest consecutive run where predicate(v) is True."""
    best, current = 0, 0
    for v in values:
        if predicate(v):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def _portfolio_insights(equity: list[dict], pairs: list[dict]) -> list[Insight]:
    insights: list[Insight] = []

    # Total return from equity curve
    valid = [e for e in equity if e.get("equity") is not None]
    if len(valid) >= MIN_SAMPLES:
        start = float(valid[0]["equity"])
        end = float(valid[-1]["equity"])
        if start > 0:
            total_return = (end - start) / start * 100
            direction = "positive" if total_return > 0 else "negative"
            insights.append(Insight(
                category="portfolio",
                headline=f"Portfolio return: {total_return:+.2f}% over {len(valid)} equity snapshots",
                detail=(
                    f"Starting equity ${start:,.2f} → ending ${end:,.2f}. "
                    f"{'Portfolio is growing — strategy is producing net positive returns.' if total_return > 0 else 'Portfolio is below starting value — review overall strategy effectiveness.'}"
                ),
                value=round(total_return, 2),
                direction=direction,
            ))

    # Realised P&L from round trips
    if len(pairs) >= MIN_SAMPLES:
        total_pnl = sum(float(p.get("pnl") or 0) for p in pairs)
        direction = "positive" if total_pnl > 0 else "negative"
        insights.append(Insight(
            category="portfolio",
            headline=f"Total realised P&L: ${total_pnl:,.2f} across {len(pairs)} completed trades",
            detail=(
                f"Sum of all completed buy→sell round trips: ${total_pnl:,.2f}. "
                f"This excludes open positions and unrealised gains/losses."
            ),
            value=round(total_pnl, 2),
            direction=direction,
        ))

    return insights
