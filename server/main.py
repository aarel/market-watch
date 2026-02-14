import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config

from .lifespan import lifespan as full_lifespan
from .lifespan import ws_manager
from .middleware import LatencyMiddleware
from .routers import alerts, analytics, observability, status, trading
from .routers import config as cfg_router
from .runtime.demo_hardening import build_demo_hardening

logger = logging.getLogger(__name__)

DEMO_MODE = os.getenv("MARKET_WATCH_DEMO_MODE", "0").lower() in {"1", "true", "yes", "on"}
USE_NOOP_LIFESPAN = os.getenv("FASTAPI_DISABLE_LIFESPAN", "0") == "1"


@asynccontextmanager
async def noop_lifespan(app):
    # Skip heavy startup (broker/coordinator) for test runs
    yield


SELECTED_LIFESPAN = full_lifespan if DEMO_MODE else (noop_lifespan if USE_NOOP_LIFESPAN else full_lifespan)


app = FastAPI(
    title="Market-Watch Trading Bot",
    description="Algorithmic trading API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=SELECTED_LIFESPAN,
)

if DEMO_MODE:
    logger.info("Demo mode: forcing full FastAPI lifespan.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add latency tracking middleware
app.add_middleware(LatencyMiddleware)

# WebSocket endpoint (MUST be before static mount)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await ws_manager.remove(websocket)


# Routers
app.include_router(status.router, prefix="/api")  # Fixed: add /api prefix
app.include_router(cfg_router.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(trading.router, prefix="/api")
app.include_router(observability.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")

# Apply demo hardening after routes are registered so dependency substitutions can be bound.
build_demo_hardening(app)

# Static UI (MUST be last to not catch API/WebSocket routes)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
