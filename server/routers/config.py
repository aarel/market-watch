from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel

from ..dependencies import get_config_manager


class ConfigUpdate(BaseModel):
    strategy: str | None = None
    watchlist: list[str] | None = None
    watchlist_mode: str | None = None
    momentum_threshold: float | None = None
    sell_threshold: float | None = None
    stop_loss_pct: float | None = None
    max_position_pct: float | None = None
    max_daily_trades: int | None = None
    max_open_positions: int | None = None
    daily_loss_limit_pct: float | None = None
    max_drawdown_pct: float | None = None
    max_sector_exposure_pct: float | None = None
    max_correlated_exposure_pct: float | None = None
    trade_interval: int | None = None
    auto_trade: bool | None = None
    top_gainers_count: int | None = None
    top_gainers_universe: str | None = None
    top_gainers_min_price: float | None = None
    top_gainers_min_volume: int | None = None
    simulation_mode: bool | None = None


router = APIRouter()


@router.get("/config")
async def get_config(cfg=Depends(get_config_manager)):
    return cfg.snapshot()


@router.post("/config")
async def update_config(updates: ConfigUpdate, cfg=Depends(get_config_manager)):
    cfg.apply_updates(updates.dict(exclude_none=True))
    cfg.save()
    return {"status": "ok", "config": cfg.snapshot()}
