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
    # Load config state
    state.config_manager.load()

    # Determine universe (temporary - will be startup arg in Week 3)
    # Check TRADING_MODE first (new approach), fall back to SIMULATION_MODE (deprecated)
    if config.TRADING_MODE == "simulation" or config.SIMULATION_MODE:
        universe = Universe.SIMULATION
    elif config.TRADING_MODE == "paper":
        universe = Universe.PAPER
    else:
        universe = Universe.LIVE

    # Broker selection and initialization with universe
    Broker = FakeBroker if universe == Universe.SIMULATION else AlpacaBroker
    state.broker = Broker(universe=universe)

    # Analytics store (universe-scoped)
    state.analytics_store = AnalyticsStore(universe) if config.ANALYTICS_ENABLED else None

    # Coordinator
    state.coordinator = Coordinator(state.broker, analytics_store=state.analytics_store)
    state.coordinator.set_broadcast_callback(ws_manager.broadcast)
    # Connect agent events to websocket
    async def handle_market_data(event):
        agent_status = state.coordinator.status()
        await ws_manager.broadcast({
            "event": "status",
            "account": event.account,
            "positions": event.positions,
            "bot": {
                "running": agent_status.get("running", False),
                "auto_trade": config.AUTO_TRADE,
                "daily_trades": agent_status.get("agents", {}).get("risk", {}).get("daily_trades", 0),
                "max_daily_trades": config.MAX_DAILY_TRADES,
                "error": state.error,
                "market_open": event.market_open,
                "universe": state.coordinator.universe.value,
                "trading_mode": config.TRADING_MODE,
            },
            "top_gainers": event.top_gainers,
            "market_indices": event.market_indices,
        })
    async def handle_signals(event):
        await ws_manager.broadcast({"event": "signals", "signals": event.signals})
    from agents import MarketDataReady, SignalsUpdated
    state.coordinator.event_bus.subscribe(MarketDataReady, handle_market_data)
    state.coordinator.event_bus.subscribe(SignalsUpdated, handle_signals)

    await state.coordinator.start()

    yield

    # Shutdown
    await state.coordinator.stop()
