import csv
import io
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config
from analytics.ab_test import run_ab_test
from analytics.enrichment import enrich_with_subsequent_performance
from analytics.whatif import run_what_if
from analytics.metrics import (
    _collapse_daily,
    compute_equity_metrics,
    compute_period_returns,
    compute_round_trip_trades,
    compute_trade_outcomes,
)

from ..dependencies import get_analytics_store, get_broker, get_state

router = APIRouter()

def _serialize_positions_for_concentration(positions, portfolio_value: float) -> list[dict]:
    rows = []
    for p in positions:
        mv = float(getattr(p, "market_value", 0) or 0)
        weight = (mv / portfolio_value * 100) if portfolio_value > 0 else 0
        qty = float(getattr(p, "qty", 0) or 0)
        price = float(
            getattr(p, "current_price", None)
            or getattr(p, "asset_current_price", None)
            or (mv / qty if qty else 0)
            or getattr(p, "avg_entry_price", 0)
            or 0
        )
        cost = float(getattr(p, "avg_entry_price", 0) or 0)
        unreal_pl = price * qty - cost * qty if qty else float(getattr(p, "unrealized_pl", 0) or 0)
        rows.append({
            "symbol": getattr(p, "symbol", ""),
            "market_value": mv,
            "qty": qty,
            "weight_pct": weight,
            "unrealized_pl": unreal_pl,
        })
    rows.sort(key=lambda r: r["weight_pct"], reverse=True)
    return rows


@router.get("/analytics/equity")
async def get_equity(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    daily = _collapse_daily(equity)
    serialized = [{"timestamp": p["timestamp"].isoformat(), "equity": p["equity"]} for p in daily]
    return {"period": period, "equity": serialized, "benchmark": [], "benchmark_symbol": ""}


@router.get("/analytics/equity.csv")
async def export_equity(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "equity",
        "portfolio_value",
        "account_value",
        "cash",
        "buying_power",
        "market_open",
        "session_id",
        "universe",
        "data_lineage_id",
        "validity_class",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in equity:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    filename = f"equity-{period}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/analytics/summary")
async def get_equity_summary(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    metrics = compute_equity_metrics(equity)
    return {"period": period, "metrics": asdict(metrics), "points": len(equity)}


@router.get("/analytics/trades")
async def get_analytics_trades(period: str = "90d", limit: int = 100, store=Depends(get_analytics_store), broker=Depends(get_broker)):
    limit = max(1, min(limit, 500))
    trades = store.load_trades(period=period, limit=limit)

    if trades and broker:
        latest_analytics_ts = max((t.get("timestamp") or "" for t in trades), default="")
        if latest_analytics_ts:
            try:
                latest_dt = datetime.fromisoformat(latest_analytics_ts.replace("Z", "+00:00"))
                if datetime.now() - latest_dt > timedelta(hours=2):
                    pass
            except:
                pass

    symbols = list({t.get("symbol", "") for t in trades if t.get("symbol")})
    asset_names = broker.get_asset_names(symbols) if broker else {}
    for t in trades:
        symbol = t.get("symbol")
        if symbol:
            t["name"] = asset_names.get(symbol, "")
    return {"period": period, "trades": trades}


@router.get("/analytics/trades/enriched")
async def get_enriched_trades(period: str = "90d", limit: int = 100, store=Depends(get_analytics_store)):
    """Return trades annotated with portfolio equity performance 1, 5, and 10 days after each trade."""
    limit = max(1, min(limit, 500))
    trades = store.load_trades(period=period, limit=limit)
    # Load all equity history so forward windows beyond the query period resolve
    equity = store.load_equity(period="all")
    enriched = enrich_with_subsequent_performance(trades, equity)
    return {"period": period, "trades": enriched}


@router.get("/analytics/trades.csv")
async def export_trades_csv(period: str = "90d", limit: int = 500, store=Depends(get_analytics_store)):
    limit = max(1, min(limit, 1000))
    trades = store.load_trades(period=period, limit=limit)
    output = io.StringIO()
    fieldnames = [
        "timestamp",
        "symbol",
        "side",
        "qty",
        "filled_avg_price",
        "notional",
        "order_id",
        "status",
        "submitted_at",
        "filled_at",
        "source",
        "time_in_force",
        "order_type",
        "session_id",
        "universe",
        "data_lineage_id",
        "validity_class",
        "name",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in trades:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    filename = f"trades-{period}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/analytics/trade_stats")
async def get_trade_stats(period: str = "90d", store=Depends(get_analytics_store)):
    trades = store.load_trades(period=period, limit=1000)
    stats = compute_trade_outcomes(trades)
    return {
        "period": period,
        "total": stats.total,
        "buys": stats.buys,
        "sells": stats.sells,
        "avg_notional": stats.avg_notional,
        "realized_pnl": stats.realized_pnl,
        "win_trades": stats.win_trades,
        "loss_trades": stats.loss_trades,
        "breakeven_trades": stats.breakeven_trades,
        "win_rate_pct": stats.win_rate_pct,
    }


@router.get("/analytics/trade_pairs")
async def get_trade_pairs(period: str = "90d", limit: int = 200, store=Depends(get_analytics_store)):
    limit = max(1, min(limit, 1000))
    trades = store.load_trades(period=period, limit=limit)
    pairs = compute_round_trip_trades(trades)
    return {"period": period, "pairs": pairs}


@router.get("/analytics/returns")
async def get_period_returns(period: str = "90d", granularity: str = "daily", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    returns = compute_period_returns(
        equity,
        granularity=granularity,
        timezone_name=config.MARKET_TIMEZONE,
    )
    return {
        "period": period,
        "granularity": granularity,
        "timezone": config.MARKET_TIMEZONE,
        "returns": returns,
    }


@router.get("/analytics/positions")
async def get_position_concentration(state=Depends(get_state), broker=Depends(get_broker)):
    if not broker:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    try:
        positions = broker.get_positions()
        account = broker.get_account()
        portfolio_value = float(getattr(account, "portfolio_value", 0) or 0)
        rows = _serialize_positions_for_concentration(positions, portfolio_value)
        return {"positions": rows, "portfolio_value": portfolio_value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WhatIfRequest(BaseModel):
    type: str                          # "position_sizing" | "stop_loss" | "hold_duration"
    period: str = "90d"
    # position_sizing
    multiplier: Optional[float] = None
    # stop_loss
    stop_loss_pct: Optional[float] = None
    # hold_duration
    extra_days: Optional[int] = None


@router.post("/analytics/what-if")
async def run_what_if_analysis(request: WhatIfRequest, store=Depends(get_analytics_store)):
    """Run a what-if scenario against historical paper trade records.

    Scenario types:
      position_sizing  — what if positions were multiplier× larger/smaller?
      stop_loss        — what if stop-loss was stop_loss_pct% (e.g. 0.03 for 3%)?
      hold_duration    — what if trades were held extra_days longer? (requires historical price data)
    """
    valid_types = {"position_sizing", "stop_loss", "hold_duration"}
    if request.type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scenario type '{request.type}'. Must be one of: {sorted(valid_types)}",
        )

    trades = store.load_trades(period=request.period, limit=1000)
    scenario = {"type": request.type}
    if request.multiplier is not None:
        scenario["multiplier"] = request.multiplier
    if request.stop_loss_pct is not None:
        scenario["stop_loss_pct"] = request.stop_loss_pct
    if request.extra_days is not None:
        scenario["extra_days"] = request.extra_days

    result = run_what_if(trades, scenario)
    return {
        "scenario_type": result.scenario_type,
        "available": result.available,
        "unavailable_reason": result.unavailable_reason,
        "baseline_pnl": result.baseline_pnl,
        "scenario_pnl": result.scenario_pnl,
        "delta_pnl": result.delta_pnl,
        "delta_pct": result.delta_pct,
        "trade_count": result.trade_count,
        "affected_trade_count": result.affected_trade_count,
        "trade_by_trade": result.trade_by_trade,
        "period": request.period,
    }


class ABTestScenario(BaseModel):
    type: str
    multiplier: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    extra_days: Optional[int] = None


class ABTestRequest(BaseModel):
    period: str = "90d"
    scenario_a: ABTestScenario
    scenario_b: ABTestScenario


@router.post("/analytics/ab-test")
async def run_ab_test_analysis(request: ABTestRequest, store=Depends(get_analytics_store)):
    """Compare two what-if scenarios against the same paper trade history.

    Both scenarios are evaluated independently against the same set of
    completed round-trip trades, then compared to identify the better
    configuration.

    Scenario format (same as /analytics/what-if):
        position_sizing: {type, multiplier}
        stop_loss:       {type, stop_loss_pct}
        hold_duration:   {type, extra_days}
    """
    valid_types = {"position_sizing", "stop_loss", "hold_duration"}
    for label, sc in (("scenario_a", request.scenario_a), ("scenario_b", request.scenario_b)):
        if sc.type not in valid_types:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid type '{sc.type}' in {label}. "
                    f"Must be one of: {sorted(valid_types)}"
                ),
            )

    trades = store.load_trades(period=request.period, limit=1000)

    def _sc_dict(sc: ABTestScenario) -> dict:
        d: dict = {"type": sc.type}
        if sc.multiplier is not None:
            d["multiplier"] = sc.multiplier
        if sc.stop_loss_pct is not None:
            d["stop_loss_pct"] = sc.stop_loss_pct
        if sc.extra_days is not None:
            d["extra_days"] = sc.extra_days
        return d

    result = run_ab_test(trades, _sc_dict(request.scenario_a), _sc_dict(request.scenario_b))

    def _serialize_whatif(w):
        return {
            "scenario_type": w.scenario_type,
            "available": w.available,
            "unavailable_reason": w.unavailable_reason,
            "baseline_pnl": w.baseline_pnl,
            "scenario_pnl": w.scenario_pnl,
            "delta_pnl": w.delta_pnl,
            "delta_pct": w.delta_pct,
            "trade_count": w.trade_count,
            "affected_trade_count": w.affected_trade_count,
            "trade_by_trade": w.trade_by_trade,
        }

    return {
        "period": request.period,
        "winner": result.winner,
        "delta_pnl": result.delta_pnl,
        "delta_pct": result.delta_pct,
        "summary": result.summary,
        "scenario_a": _serialize_whatif(result.scenario_a),
        "scenario_b": _serialize_whatif(result.scenario_b),
    }


@router.get("/analytics/report")
async def get_analytics_report(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    summary = compute_equity_metrics(equity)
    trades = store.load_trades(period=period, limit=200)
    stats = compute_trade_outcomes(trades)
    pairs = compute_round_trip_trades(trades)
    daily_returns = compute_period_returns(equity, granularity="daily", timezone_name=config.MARKET_TIMEZONE)
    weekly_returns = compute_period_returns(equity, granularity="weekly", timezone_name=config.MARKET_TIMEZONE)
    monthly_returns = compute_period_returns(equity, granularity="monthly", timezone_name=config.MARKET_TIMEZONE)

    def _render_return_rows(rows):
        if not rows:
            return '<tr><td colspan="4">No return data</td></tr>'
        lines = []
        for row in rows[-10:]:
            lines.append(
                "<tr>"
                f"<td>{row['period']}</td>"
                f"<td>{row['start_equity']:.2f}</td>"
                f"<td>{row['end_equity']:.2f}</td>"
                f"<td>{row['return_pct']:.2f}%</td>"
                "</tr>"
            )
        return "\n".join(lines)

    def _render_trade_rows(rows):
        if not rows:
            return '<tr><td colspan="6">No completed round-trip trades</td></tr>'
        lines = []
        for trade in rows[-50:]:
            ts = trade.get("timestamp") or ""
            lines.append(
                "<tr>"
                f"<td>{ts}</td>"
                f"<td>{trade.get('symbol', '')}</td>"
                f"<td>{trade.get('qty', 0):.4f}</td>"
                f"<td>{trade.get('buy_price', 0):.2f}</td>"
                f"<td>{trade.get('sell_price', 0):.2f}</td>"
                f"<td>{trade.get('pnl', 0):.2f}</td>"
                "</tr>"
            )
        return "\n".join(lines)

    html = f"""
    <html>
    <head>
      <title>Analytics Report - {period}</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
        h1, h2 {{ margin-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f4f4f4; }}
        .section {{ margin-top: 24px; }}
      </style>
    </head>
    <body>
    <h1>Analytics Report ({period.upper()})</h1>
    <h2>Equity Metrics</h2>
    <ul>
      <li>Total Return: {summary.total_return_pct:.2f}%</li>
      <li>Max Drawdown: {summary.max_drawdown_pct:.2f}%</li>
      <li>Volatility: {summary.volatility_pct:.2f}%</li>
      <li>Sharpe: {summary.sharpe_ratio:.2f}</li>
    </ul>
    <h2>Trade Stats</h2>
    <ul>
      <li>Total trades: {stats.total} (Buys {stats.buys} / Sells {stats.sells})</li>
      <li>Win rate: {stats.win_rate_pct:.1f}%</li>
      <li>Realized P&L: ${stats.realized_pnl:,.2f}</li>
      <li>Avg notional: ${stats.avg_notional:,.2f}</li>
    </ul>
    <div class="section">
      <h2>Period Returns (Daily)</h2>
      <table>
        <thead><tr><th>Period</th><th>Start Equity</th><th>End Equity</th><th>Return %</th></tr></thead>
        <tbody>{_render_return_rows(daily_returns)}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Period Returns (Weekly)</h2>
      <table>
        <thead><tr><th>Period</th><th>Start Equity</th><th>End Equity</th><th>Return %</th></tr></thead>
        <tbody>{_render_return_rows(weekly_returns)}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Period Returns (Monthly)</h2>
      <table>
        <thead><tr><th>Period</th><th>Start Equity</th><th>End Equity</th><th>Return %</th></tr></thead>
        <tbody>{_render_return_rows(monthly_returns)}</tbody>
      </table>
    </div>
    <div class="section">
      <h2>Round-Trip Trades</h2>
      <table>
        <thead><tr><th>Timestamp</th><th>Symbol</th><th>Qty</th><th>Buy</th><th>Sell</th><th>P&L</th></tr></thead>
        <tbody>{_render_trade_rows(pairs)}</tbody>
      </table>
    </div>
    <p>Export to PDF by wrapping this endpoint with a headless browser later.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html, status_code=200)
