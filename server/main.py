import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

import config
from .lifespan import lifespan as full_lifespan, ws_manager
from .routers import status, config as cfg_router, analytics, trading, observability
from .dependencies import get_state

USE_NOOP_LIFESPAN = os.getenv("FASTAPI_DISABLE_LIFESPAN", "0") == "1"


@asynccontextmanager
async def noop_lifespan(app):
    # Skip heavy startup (broker/coordinator) for test runs
    yield


app = FastAPI(
    title="Market-Watch Trading Bot",
    description="Algorithmic trading API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=noop_lifespan if USE_NOOP_LIFESPAN else full_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Static UI (MUST be last to not catch API/WebSocket routes)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
