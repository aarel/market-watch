"""Configuration manager to load, validate, and persist runtime config."""
import json
import os
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

import config
from universe import Universe, get_data_path


class RuntimeConfig(BaseModel):
    """Runtime configuration with strict type validation via Pydantic.

    This prevents the bool("false") bug where string "false" evaluates to True.
    Pydantic handles proper string-to-bool conversion ("true"/"false" strings).
    """
    strategy: str = config.STRATEGY
    watchlist: List[str] = Field(default_factory=lambda: config.WATCHLIST.copy())
    watchlist_mode: str = config.WATCHLIST_MODE
    momentum_threshold: float = config.MOMENTUM_THRESHOLD
    sell_threshold: float = config.SELL_THRESHOLD
    stop_loss_pct: float = config.STOP_LOSS_PCT
    max_position_pct: float = config.MAX_POSITION_PCT
    max_daily_trades: int = config.MAX_DAILY_TRADES
    max_open_positions: int = config.MAX_OPEN_POSITIONS
    daily_loss_limit_pct: float = config.DAILY_LOSS_LIMIT_PCT
    max_drawdown_pct: float = config.MAX_DRAWDOWN_PCT
    max_sector_exposure_pct: float = config.MAX_SECTOR_EXPOSURE_PCT
    max_correlated_exposure_pct: float = config.MAX_CORRELATED_EXPOSURE_PCT
    trade_interval: int = config.TRADE_INTERVAL_MINUTES
    auto_trade: bool = config.AUTO_TRADE
    top_gainers_count: int = config.TOP_GAINERS_COUNT
    top_gainers_universe: str = config.TOP_GAINERS_UNIVERSE
    top_gainers_min_price: float = config.TOP_GAINERS_MIN_PRICE
    top_gainers_min_volume: int = config.TOP_GAINERS_MIN_VOLUME

    model_config = {"frozen": False}  # Allow field updates

    @field_validator('auto_trade', mode='before')
    @classmethod
    def validate_bool_from_string(cls, v):
        """Strict boolean parsing to prevent bool("false") = True bug.

        Accepts: bool, "true"/"false" (case-insensitive), 1/0
        Rejects: any other string with clear error message
        """
        if isinstance(v, bool):
            return v
        if isinstance(v, int):
            return bool(v)
        if isinstance(v, str):
            lower = v.lower().strip()
            if lower in ('true', '1', 'yes', 'on'):
                return True
            elif lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(
                    f"Invalid boolean string: '{v}'. "
                    f"Accepted values: true/false, yes/no, on/off, 1/0"
                )
        raise TypeError(f"Cannot convert {type(v).__name__} to bool")


PERSISTED_CONFIG_KEYS = set(RuntimeConfig.model_fields.keys())


class ConfigManager:
    def __init__(self, path: str = None, universe: Optional[Universe] = None):
        """Initialize ConfigManager with optional universe-scoped path.

        Args:
            path: Explicit path override (for testing)
            universe: Universe for scoped config (generates path: data/{universe}/config_state.json)

        If both path and universe are None, falls back to config.CONFIG_STATE_PATH for
        backward compatibility, but this is deprecated - universe should always be provided.
        """
        if path:
            self.path = path
        elif universe:
            # Universe-scoped path: data/{universe}/config_state.json
            self.path = get_data_path(universe, "config_state.json")
        else:
            # Deprecated fallback for backward compatibility
            self.path = config.CONFIG_STATE_PATH

        self.universe = universe
        self.state = RuntimeConfig()
        self.load()

    def refresh_from_config(self):
        """Refresh the runtime snapshot from the live config module."""
        self.state = RuntimeConfig(
            strategy=config.STRATEGY,
            watchlist=list(config.WATCHLIST),
            watchlist_mode=config.WATCHLIST_MODE,
            momentum_threshold=config.MOMENTUM_THRESHOLD,
            sell_threshold=config.SELL_THRESHOLD,
            stop_loss_pct=config.STOP_LOSS_PCT,
            max_position_pct=config.MAX_POSITION_PCT,
            max_daily_trades=config.MAX_DAILY_TRADES,
            max_open_positions=config.MAX_OPEN_POSITIONS,
            daily_loss_limit_pct=config.DAILY_LOSS_LIMIT_PCT,
            max_drawdown_pct=config.MAX_DRAWDOWN_PCT,
            max_sector_exposure_pct=config.MAX_SECTOR_EXPOSURE_PCT,
            max_correlated_exposure_pct=config.MAX_CORRELATED_EXPOSURE_PCT,
            trade_interval=config.TRADE_INTERVAL_MINUTES,
            auto_trade=config.AUTO_TRADE,
            top_gainers_count=config.TOP_GAINERS_COUNT,
            top_gainers_universe=config.TOP_GAINERS_UNIVERSE,
            top_gainers_min_price=config.TOP_GAINERS_MIN_PRICE,
            top_gainers_min_volume=config.TOP_GAINERS_MIN_VOLUME,
        )

    def snapshot(self) -> dict:
        return self.state.model_dump()

    def load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        self.apply_updates(data)

    def save(self):
        if not self.path:
            return
        # Ensure we persist the latest in-memory config values
        self.refresh_from_config()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.snapshot(), f, indent=2)

    def apply_updates(self, updates: dict):
        """Apply updates with Pydantic validation.

        This prevents the bool("false") bug by using Pydantic's strict type validation.
        Invalid updates will raise ValidationError with clear error messages.
        """
        # Filter to only allowed keys
        filtered_updates = {k: v for k, v in updates.items() if k in PERSISTED_CONFIG_KEYS}

        # Get current state as dict
        current_state = self.state.model_dump()

        # Merge updates
        current_state.update(filtered_updates)

        # Validate and create new state (Pydantic will validate all fields)
        try:
            self.state = RuntimeConfig(**current_state)
        except Exception as e:
            # Re-raise with context for debugging
            raise ValueError(f"Config validation failed: {e}") from e

        # Reflect back into config module for legacy consumers
        self._apply_to_config()

    def _apply_to_config(self):
        # Minimal legacy sync
        cfg = self.state
        config.STRATEGY = cfg.strategy
        config.WATCHLIST = cfg.watchlist
        config.WATCHLIST_MODE = cfg.watchlist_mode
        config.MOMENTUM_THRESHOLD = cfg.momentum_threshold
        config.SELL_THRESHOLD = cfg.sell_threshold
        config.STOP_LOSS_PCT = cfg.stop_loss_pct
        config.MAX_POSITION_PCT = cfg.max_position_pct
        config.MAX_DAILY_TRADES = cfg.max_daily_trades
        config.MAX_OPEN_POSITIONS = cfg.max_open_positions
        config.DAILY_LOSS_LIMIT_PCT = cfg.daily_loss_limit_pct
        config.MAX_DRAWDOWN_PCT = cfg.max_drawdown_pct
        config.MAX_SECTOR_EXPOSURE_PCT = cfg.max_sector_exposure_pct
        config.MAX_CORRELATED_EXPOSURE_PCT = cfg.max_correlated_exposure_pct
        config.TRADE_INTERVAL_MINUTES = cfg.trade_interval
        config.AUTO_TRADE = cfg.auto_trade
        config.TOP_GAINERS_COUNT = cfg.top_gainers_count
        config.TOP_GAINERS_UNIVERSE = cfg.top_gainers_universe
        config.TOP_GAINERS_MIN_PRICE = cfg.top_gainers_min_price
        config.TOP_GAINERS_MIN_VOLUME = cfg.top_gainers_min_volume
