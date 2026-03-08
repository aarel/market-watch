"""Configuration manager to load, validate, and persist runtime config."""
import asyncio
import json
import logging
import os
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field, field_validator

import config
from universe import Universe, get_data_path

if TYPE_CHECKING:
    from agents.event_bus import EventBus

logger = logging.getLogger(__name__)


class RuntimeConfig(BaseModel):
    """Runtime configuration with strict type validation via Pydantic.

    This prevents the bool("false") bug where string "false" evaluates to True.
    Pydantic handles proper string-to-bool conversion ("true"/"false" strings).
    """
    strategy: str = config.STRATEGY
    watchlist: list[str] = Field(default_factory=lambda: config.WATCHLIST.copy())
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
    rvol_threshold: float = config.RVOL_THRESHOLD
    trade_interval: int = config.TRADE_INTERVAL_MINUTES
    auto_trade: bool = config.AUTO_TRADE
    top_gainers_count: int = config.TOP_GAINERS_COUNT
    top_gainers_universe: str = config.TOP_GAINERS_UNIVERSE
    top_gainers_min_price: float = config.TOP_GAINERS_MIN_PRICE
    top_gainers_min_volume: int = config.TOP_GAINERS_MIN_VOLUME

    # Alert configuration
    alerts_enabled: bool = config.ALERTS_ENABLED
    alert_email_enabled: bool = config.ALERT_EMAIL_ENABLED
    alert_webhook_enabled: bool = config.ALERT_WEBHOOK_ENABLED

    # Market Awareness (Phase 9)
    avoid_open_minutes: int = config.AVOID_OPEN_MINUTES
    avoid_close_minutes: int = config.AVOID_CLOSE_MINUTES
    earnings_blackout_days: int = config.EARNINGS_BLACKOUT_DAYS
    fomc_blackout_enabled: bool = config.FOMC_BLACKOUT_ENABLED

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
            if lower in ('false', '0', 'no', 'off'):
                return False
            raise ValueError(
                f"Invalid boolean string: '{v}'. "
                f"Accepted values: true/false, yes/no, on/off, 1/0"
            )
        raise TypeError(f"Cannot convert {type(v).__name__} to bool")


PERSISTED_CONFIG_KEYS = set(RuntimeConfig.model_fields.keys())


class ConfigManager:
    def __init__(
        self,
        path: str = None,
        universe: Universe | None = None,
        event_bus: Optional["EventBus"] = None
    ):
        """Initialize ConfigManager with universe or explicit path.

        Args:
            path: Explicit path override (for testing only)
            universe: Universe for scoped config (generates path: data/{universe}/config_state.json)
            event_bus: Optional event bus for broadcasting config changes

        Raises:
            TypeError: If both path and universe are None (universe is required in production)
        """
        if path:
            # Explicit path provided (testing only)
            self.path = path
        elif universe:
            # Universe-scoped path: data/{universe}/config_state.json
            self.path = get_data_path(universe, "config_state.json")
        else:
            # No fallback - universe is required unless explicit path provided
            raise TypeError(
                "ConfigManager requires either 'universe' parameter (production) "
                "or 'path' parameter (testing only). "
                "Example: ConfigManager(universe=Universe.PAPER)"
            )

        self.universe = universe
        self.event_bus = event_bus
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
            rvol_threshold=config.RVOL_THRESHOLD,
            trade_interval=config.TRADE_INTERVAL_MINUTES,
            auto_trade=config.AUTO_TRADE,
            top_gainers_count=config.TOP_GAINERS_COUNT,
            top_gainers_universe=config.TOP_GAINERS_UNIVERSE,
            top_gainers_min_price=config.TOP_GAINERS_MIN_PRICE,
            top_gainers_min_volume=config.TOP_GAINERS_MIN_VOLUME,
            alerts_enabled=config.ALERTS_ENABLED,
            alert_email_enabled=config.ALERT_EMAIL_ENABLED,
            alert_webhook_enabled=config.ALERT_WEBHOOK_ENABLED,
            avoid_open_minutes=config.AVOID_OPEN_MINUTES,
            avoid_close_minutes=config.AVOID_CLOSE_MINUTES,
            earnings_blackout_days=config.EARNINGS_BLACKOUT_DAYS,
            fomc_blackout_enabled=config.FOMC_BLACKOUT_ENABLED,
        )

    def snapshot(self) -> dict:
        return self.state.model_dump()

    def load(self):
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
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

        Emits ConfigUpdated event if event_bus is available.
        """
        # Filter to only allowed keys
        filtered_updates = {k: v for k, v in updates.items() if k in PERSISTED_CONFIG_KEYS}

        if not filtered_updates:
            return  # No valid updates

        # Get current state as dict
        current_state = self.state.model_dump()

        # Track what changed
        changed_keys = [k for k in filtered_updates if filtered_updates[k] != current_state.get(k)]

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

        # Emit ConfigUpdated event if event bus available and changes occurred
        if self.event_bus and changed_keys:
            self._emit_config_updated(changed_keys)

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
        config.RVOL_THRESHOLD = cfg.rvol_threshold
        config.TRADE_INTERVAL_MINUTES = cfg.trade_interval
        config.AUTO_TRADE = cfg.auto_trade
        config.TOP_GAINERS_COUNT = cfg.top_gainers_count
        config.TOP_GAINERS_UNIVERSE = cfg.top_gainers_universe
        config.TOP_GAINERS_MIN_PRICE = cfg.top_gainers_min_price
        config.TOP_GAINERS_MIN_VOLUME = cfg.top_gainers_min_volume
        config.ALERTS_ENABLED = cfg.alerts_enabled
        config.ALERT_EMAIL_ENABLED = cfg.alert_email_enabled
        config.ALERT_WEBHOOK_ENABLED = cfg.alert_webhook_enabled
        config.AVOID_OPEN_MINUTES = cfg.avoid_open_minutes
        config.AVOID_CLOSE_MINUTES = cfg.avoid_close_minutes
        config.EARNINGS_BLACKOUT_DAYS = cfg.earnings_blackout_days
        config.FOMC_BLACKOUT_ENABLED = cfg.fomc_blackout_enabled

    def _emit_config_updated(self, changed_keys: list[str]):
        """Emit ConfigUpdated event to notify agents of config changes.

        Args:
            changed_keys: List of configuration keys that changed
        """
        if not self.event_bus or not self.universe:
            return

        try:
            from agents.events import ConfigUpdated
            from universe import UniverseContext

            # Get session_id from event bus's context
            context = getattr(self.event_bus, '_context', None)
            if not context:
                # Fallback: create temporary context
                context = UniverseContext(self.universe)

            event = ConfigUpdated(
                universe=self.universe,
                session_id=context.session_id,
                source="ConfigManager",
                changed_keys=changed_keys,
                config_snapshot=self.snapshot(),
            )

            # Schedule async publish in event loop
            asyncio.create_task(self.event_bus.publish(event))
            logger.info(f"Config updated: {', '.join(changed_keys)}")

        except Exception as e:
            logger.error(f"Failed to emit ConfigUpdated event: {e}")
