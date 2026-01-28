import csv
import io
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse

from analytics.metrics import compute_equity_metrics, compute_trade_outcomes
from dataclasses import asdict

from ..dependencies import get_analytics_store, get_broker
from ..dependencies import get_state

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
    return {"period": period, "equity": equity, "benchmark": [], "benchmark_symbol": ""}


@router.get("/analytics/equity.csv")
async def export_equity(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    output = io.StringIO()
    fieldnames = ["timestamp", "equity", "portfolio_value", "account_value"]
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


@router.get("/analytics/report")
async def get_analytics_report(period: str = "30d", store=Depends(get_analytics_store)):
    equity = store.load_equity(period=period)
    summary = compute_equity_metrics(equity)
    trades = store.load_trades(period=period, limit=200)
    stats = compute_trade_outcomes(trades)

    html = f"""
    <html><head><title>Analytics Report - {period}</title></head><body>
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
    <p>Export to PDF by wrapping this endpoint with a headless browser later.</p>
    </body></html>
    """
    return HTMLResponse(content=html, status_code=200)
