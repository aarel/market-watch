import os
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

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

def create_metrics(registry: CollectorRegistry | None = None):
    """Build metrics against an explicit registry for test-safe isolation."""
    registry = registry or CollectorRegistry()
    request_count = Counter(
        "http_requests_total",
        "Total number of HTTP requests",
        ["method", "path", "status"],
        registry=registry,
    )
    request_error_count = Counter(
        "http_request_errors_total",
        "Total number of HTTP 5xx responses",
        ["method", "path"],
        registry=registry,
    )
    request_latency = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        registry=registry,
    )
    return {
        "registry": registry,
        "request_count": request_count,
        "request_error_count": request_error_count,
        "request_latency": request_latency,
    }


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

app.state.metrics = create_metrics()


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = time.perf_counter()
    response = None
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        path = request.url.path
        method = request.method
        duration = time.perf_counter() - start
        metrics = app.state.metrics
        metrics["request_count"].labels(method=method, path=path, status=str(status_code)).inc()
        metrics["request_latency"].labels(method=method, path=path).observe(duration)
        if status_code >= 500:
            metrics["request_error_count"].labels(method=method, path=path).inc()


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(app.state.metrics["registry"]), media_type=CONTENT_TYPE_LATEST)

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
