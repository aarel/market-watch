import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response

import config

from ..dependencies import get_analytics_store, get_broker, get_state

router = APIRouter()


@router.post("/bot/start")
async def start_bot(state=Depends(get_state)):
    if not state.coordinator:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    config.AUTO_TRADE = True
    return {"status": "ok", "auto_trade": True}


@router.post("/bot/stop")
async def stop_bot(state=Depends(get_state)):
    if not state.coordinator:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    config.AUTO_TRADE = False
    return {"status": "ok", "auto_trade": False}


@router.post("/risk/breaker/reset")
async def reset_breaker(state=Depends(get_state)):
    if not state.coordinator:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    status = state.coordinator.reset_circuit_breaker()
    return status


@router.post("/trade/manual")
async def manual_trade(symbol: str, action: str, amount: float = None, qty: float = None, mode: str = "notional", state=Depends(get_state)):
    if not state.coordinator:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    result = await state.coordinator.manual_trade(symbol, action, amount, qty, mode)
    return result


@router.get("/assets/names")
async def get_asset_names(symbols: str, broker=Depends(get_broker)):
    """Get display names for asset symbols"""
    if not broker:
        return {"names": {}}

    symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
    if not symbol_list:
        return {"names": {}}

    try:
        names = broker.get_asset_names(symbol_list)
        return {"names": names}
    except Exception:
        # Return empty names on error - UI will handle gracefully
        return {"names": {}}


@router.get("/trades")
async def get_recent_trades(limit: int = 30, broker=Depends(get_broker)):
    """Compatibility endpoint: returns recent trades from broker"""
    if not broker:
        return {"trades": []}

    # Check if broker has list_orders method (real Alpaca broker)
    if hasattr(broker, 'list_orders'):
        try:
            orders = broker.list_orders(status="closed", limit=limit)
            trades = []
            for order in orders:
                if order.filled_at:
                    filled_at_iso = order.filled_at.isoformat() if order.filled_at else None
                    # Source is stamped into client_order_id as "{auto|manual}-{symbol}-{ts}"
                    client_oid = getattr(order, 'client_order_id', '') or ''
                    prefix = client_oid.split('-')[0] if client_oid else ''
                    source = prefix if prefix in ('auto', 'manual') else 'unknown'
                    trades.append({
                        "id": order.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "qty": float(order.qty or 0),
                        "filled_qty": float(order.filled_qty or 0),
                        "filled_avg_price": float(order.filled_avg_price or 0),
                        "notional": float(order.notional or 0) if order.notional else None,
                        "filled_at": filled_at_iso,
                        "timestamp": filled_at_iso,
                        "status": order.status,
                        "source": source,
                    })
            return {"trades": trades}
        except Exception as e:
            return {"trades": [], "error": str(e)}
    else:
        # FakeBroker: return empty list (UI should use /api/analytics/trades instead)
        return {"trades": []}


@router.get("/trades/export")
async def export_trades(period: str = "90d", limit: int = 500, store=Depends(get_analytics_store)):
    """Export trades to CSV"""
    limit = max(1, min(limit, 1000))
    trades = store.load_trades(period=period, limit=limit)
    output = io.StringIO()
    if trades:
        fieldnames = list(trades[0].keys())
    else:
        fieldnames = ["timestamp", "symbol", "action", "qty", "notional", "filled_avg_price", "order_id"]
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
