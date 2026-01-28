from fastapi import APIRouter, Depends, HTTPException

from agents import RiskCheckPassed
import config
from ..dependencies import get_state, get_broker

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


@router.get("/trades")
async def get_recent_trades(limit: int = 30, broker=Depends(get_broker)):
    """Compatibility endpoint: returns recent trades from broker"""
    if not broker:
        return {"trades": []}

    # Check if broker has get_orders method (real Alpaca broker)
    if hasattr(broker, 'get_orders'):
        try:
            orders = broker.get_orders(status="closed", limit=limit)
            trades = []
            for order in orders:
                if order.filled_at:
                    trades.append({
                        "id": order.id,
                        "symbol": order.symbol,
                        "side": order.side,
                        "qty": float(order.qty or 0),
                        "filled_qty": float(order.filled_qty or 0),
                        "filled_avg_price": float(order.filled_avg_price or 0),
                        "notional": float(order.notional or 0) if order.notional else None,
                        "timestamp": order.filled_at.isoformat() if order.filled_at else None,
                        "status": order.status
                    })
            return {"trades": trades}
        except Exception as e:
            return {"trades": [], "error": str(e)}
    else:
        # FakeBroker: return empty list (UI should use /api/analytics/trades instead)
        return {"trades": []}
