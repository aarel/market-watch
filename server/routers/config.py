import json
import re
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from alerts.runtime import configure_alerts

from ..config_audit import append_audit
from ..config_profiles import delete_profile, list_profiles, load_profile, save_profile
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
    rvol_threshold: float | None = None
    trade_interval: int | None = None
    auto_trade: bool | None = None
    top_gainers_count: int | None = None
    top_gainers_universe: str | None = None
    top_gainers_min_price: float | None = None
    top_gainers_min_volume: int | None = None
    simulation_mode: bool | None = None
    alerts_enabled: bool | None = None
    alert_email_enabled: bool | None = None
    alert_webhook_enabled: bool | None = None


router = APIRouter()


@router.get("/config")
async def get_config(cfg=Depends(get_config_manager)):
    return cfg.snapshot()


@router.post("/config")
async def update_config(updates: ConfigUpdate, cfg=Depends(get_config_manager)):
    old = cfg.snapshot()
    cfg.apply_updates(updates.dict(exclude_none=True))
    cfg.save()
    new = cfg.snapshot()
    universe_val = cfg.universe.value if cfg.universe else "unknown"
    append_audit(universe_val, old, new)
    configure_alerts(new)
    return {"status": "ok", "config": new}


# ---------------------------------------------------------------------------
# Config profiles
# ---------------------------------------------------------------------------

class SaveProfileRequest(BaseModel):
    name: str


_NAME_RE = re.compile(r'^[A-Za-z0-9_\-]{1,64}$')


def _check_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid profile name '{name}'. "
                "Use 1-64 characters: letters, digits, underscore, hyphen."
            ),
        )


@router.get("/config/profiles")
async def get_profiles(cfg=Depends(get_config_manager)):
    """List all saved config profiles."""
    return {"profiles": list_profiles()}


@router.post("/config/profiles")
async def create_profile(req: SaveProfileRequest, cfg=Depends(get_config_manager)):
    """Save the current config as a named profile."""
    _check_name(req.name)
    try:
        save_profile(req.name, cfg.snapshot())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"status": "ok", "name": req.name}


@router.post("/config/profiles/{name}/load")
async def load_profile_endpoint(name: str, cfg=Depends(get_config_manager)):
    """Load a named profile into the current config."""
    _check_name(name)
    try:
        profile_data = load_profile(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found.")
    old = cfg.snapshot()
    cfg.apply_updates(profile_data)
    cfg.save()
    new = cfg.snapshot()
    universe_val = cfg.universe.value if cfg.universe else "unknown"
    append_audit(universe_val, old, new)
    configure_alerts(new)
    return {"status": "ok", "name": name, "config": new}


@router.delete("/config/profiles/{name}")
async def delete_profile_endpoint(name: str, cfg=Depends(get_config_manager)):
    """Delete a named profile."""
    _check_name(name)
    existed = delete_profile(name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found.")
    return {"status": "ok", "name": name}


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

@router.get("/config/export")
async def export_config(cfg=Depends(get_config_manager)):
    """Download the current config as a JSON file."""
    snapshot = cfg.snapshot()
    snapshot["_exported_at"] = datetime.now().isoformat()
    universe_val = cfg.universe.value if cfg.universe else "unknown"
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"config_{universe_val}_{date_str}.json"
    content = json.dumps(snapshot, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/config/import")
async def import_config(file: UploadFile, cfg=Depends(get_config_manager)):
    """Upload and apply a previously exported config JSON file."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=422, detail="File must be a .json file.")
    try:
        raw = await file.read()
        data = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid JSON file.")

    # Strip metadata keys
    clean = {k: v for k, v in data.items() if not k.startswith("_")}

    old = cfg.snapshot()
    try:
        cfg.apply_updates(clean)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Config validation failed: {e}")
    cfg.save()
    new = cfg.snapshot()
    universe_val = cfg.universe.value if cfg.universe else "unknown"
    append_audit(universe_val, old, new)
    configure_alerts(new)
    return {"status": "ok", "config": new}
