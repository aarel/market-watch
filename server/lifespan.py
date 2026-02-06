import asyncio
import os
import json
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI

import config
from broker import AlpacaBroker
from fake_broker import FakeBroker
from agents import Coordinator
from analytics.store import AnalyticsStore
from universe import Universe
from .state import AppState
from .events import WebsocketManager
from .dependencies import get_state


ws_manager = WebsocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = get_state()

    # Determine universe from TRADING_MODE
    if config.TRADING_MODE == "simulation":
        universe = Universe.SIMULATION
    elif config.TRADING_MODE == "paper":
        universe = Universe.PAPER
    elif config.TRADING_MODE == "live":
        universe = Universe.LIVE
    else:
        raise ValueError(
            f"Invalid TRADING_MODE: '{config.TRADING_MODE}'. "
            f"Must be 'simulation', 'paper', or 'live'"
        )

    # Initialize universe-scoped config manager and load state
    state.set_universe(universe)  # This also creates universe-scoped ConfigManager
    state.config_manager.load()

    # Rebuild universe-bound components via factories
    def broker_factory(u: Universe):
        Broker = FakeBroker if u == Universe.SIMULATION else AlpacaBroker
        return Broker(universe=u)

    def analytics_factory(u: Universe):
        return AnalyticsStore(u) if config.ANALYTICS_ENABLED else None

    def coordinator_factory(broker, store):
        coord = Coordinator(broker, analytics_store=store, universe=broker.universe)
        coord.set_broadcast_callback(ws_manager.broadcast)
        return coord

    state.rebuild_for_universe(
        universe,
        broker_factory=broker_factory,
        analytics_factory=analytics_factory,
        coordinator_factory=coordinator_factory,
    )
    # Connect agent events to websocket
    async def broadcast_status(account=None, positions=None, market_open=None, top_gainers=None, market_indices=None):
        """Broadcast current status to websocket clients."""
        agent_status = state.coordinator.status()

        # If account/positions not provided, fetch from broker
        if account is None or positions is None:
            try:
                if account is None:
                    acct = state.broker.get_account()
                    account = {
                        "portfolio_value": float(acct.portfolio_value),
                        "buying_power": float(acct.buying_power),
                        "cash": float(acct.cash),
                        "equity": float(acct.equity),
                    }
                if positions is None:
                    positions = []
                    for pos in state.broker.get_positions():
                        positions.append({
                            "symbol": pos.symbol,
                            "qty": float(pos.qty),
                            "market_value": float(pos.market_value),
                            "avg_entry_price": float(pos.avg_entry_price),
                            "unrealized_pl": float(pos.unrealized_pl),
                            "unrealized_plpc": float(pos.unrealized_plpc) * 100,
                        })
            except Exception as e:
                print(f"lifespan: Error fetching account/positions for status broadcast: {e}")

        if market_open is None:
            try:
                market_open = state.broker.is_market_open()
            except Exception:
                market_open = False

        await ws_manager.broadcast({
            "event": "status",
            "account": account,
            "positions": positions,
            "bot": {
                "running": agent_status.get("running", False),
                "auto_trade": config.AUTO_TRADE,
                "daily_trades": agent_status.get("agents", {}).get("risk", {}).get("daily_trades", 0),
                "max_daily_trades": config.MAX_DAILY_TRADES,
                "error": state.error,
                "market_open": market_open,
                "universe": state.coordinator.universe.value,
                "trading_mode": config.TRADING_MODE,
            },
            "config": state.config_manager.snapshot(),
            "agents": agent_status.get("agents", {}),
            "top_gainers": top_gainers or [],
            "market_indices": market_indices or [],
        })

    async def handle_market_data(event):
        await broadcast_status(
            account=event.account,
            positions=event.positions,
            market_open=event.market_open,
            top_gainers=event.top_gainers,
            market_indices=event.market_indices,
        )

    async def handle_signals(event):
        await ws_manager.broadcast({"event": "signals", "signals": event.signals})

    async def handle_order_executed(event):
        """Broadcast status update after trade execution to refresh daily_trades count."""
        await broadcast_status()

    from agents import MarketDataReady, SignalsUpdated, OrderExecuted
    state.coordinator.event_bus.subscribe(MarketDataReady, handle_market_data)
    state.coordinator.event_bus.subscribe(SignalsUpdated, handle_signals)
    state.coordinator.event_bus.subscribe(OrderExecuted, handle_order_executed)

    await state.coordinator.start()

    yield

    # Shutdown
    await state.coordinator.stop()
