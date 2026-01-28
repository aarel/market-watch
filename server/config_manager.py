"""Configuration manager to load, validate, and persist runtime config."""
import json
import os
from dataclasses import dataclass, asdict, field
from typing import List

import config


@dataclass
class RuntimeConfig:
    strategy: str = config.STRATEGY
    watchlist: List[str] = field(default_factory=lambda: config.WATCHLIST.copy())
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
    simulation_mode: bool = config.SIMULATION_MODE
    top_gainers_count: int = config.TOP_GAINERS_COUNT
    top_gainers_universe: str = config.TOP_GAINERS_UNIVERSE
    top_gainers_min_price: float = config.TOP_GAINERS_MIN_PRICE
    top_gainers_min_volume: int = config.TOP_GAINERS_MIN_VOLUME


PERSISTED_CONFIG_KEYS = set(RuntimeConfig().__dict__.keys())


class ConfigManager:
    def __init__(self, path: str = None):
        self.path = path or config.CONFIG_STATE_PATH
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
            simulation_mode=config.SIMULATION_MODE,
            top_gainers_count=config.TOP_GAINERS_COUNT,
            top_gainers_universe=config.TOP_GAINERS_UNIVERSE,
            top_gainers_min_price=config.TOP_GAINERS_MIN_PRICE,
            top_gainers_min_volume=config.TOP_GAINERS_MIN_VOLUME,
        )

    def snapshot(self) -> dict:
        return asdict(self.state)

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
        for key, value in updates.items():
            if key not in PERSISTED_CONFIG_KEYS:
                continue
            try:
                if isinstance(getattr(self.state, key), bool):
                    setattr(self.state, key, bool(value))
                elif isinstance(getattr(self.state, key), int):
                    setattr(self.state, key, int(value))
                elif isinstance(getattr(self.state, key), float):
                    setattr(self.state, key, float(value))
                elif isinstance(getattr(self.state, key), list):
                    setattr(self.state, key, list(value))
                else:
                    setattr(self.state, key, value)
            except Exception:
                continue
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
        config.SIMULATION_MODE = cfg.simulation_mode
        config.TOP_GAINERS_COUNT = cfg.top_gainers_count
        config.TOP_GAINERS_UNIVERSE = cfg.top_gainers_universe
        config.TOP_GAINERS_MIN_PRICE = cfg.top_gainers_min_price
        config.TOP_GAINERS_MIN_VOLUME = cfg.top_gainers_min_volume
