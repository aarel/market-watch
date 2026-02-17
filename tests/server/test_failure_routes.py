from __future__ import annotations

from collections.abc import Iterator

import pytest
import httpx
from fastapi import FastAPI, HTTPException

from server.dependencies import get_config_manager
from server.routers import config as cfg_router
from server.routers import observability
from server.runtime.demo_hardening import get_safe_universe_context
from server.state import AppState
from universe import Universe


@pytest.fixture
def isolated_state() -> Iterator[AppState]:
    state = AppState.instance()
    snapshot = {
        "broker": state.broker,
        "coordinator": state.coordinator,
        "error": state.error,
        "config_manager": state.config_manager,
        "universe_context": state.universe_context,
        "analytics_store": state.analytics_store,
    }
    state.broker = None
    state.coordinator = None
    state.error = None
    state.config_manager = None
    state.universe_context = None
    state.analytics_store = None
    try:
        yield state
    finally:
        for key, value in snapshot.items():
            setattr(state, key, value)


@pytest.mark.anyio
async def test_degraded_config_route(isolated_state: AppState):
    app = FastAPI()
    app.include_router(cfg_router.router, prefix="/api")

    async def _missing_config():
        raise HTTPException(status_code=503, detail="Config manager unavailable; runtime not fully initialized")

    app.dependency_overrides[get_config_manager] = _missing_config

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/config")
    assert response.status_code == 503
    assert response.json()["detail"] == "Config manager unavailable; runtime not fully initialized"


@pytest.mark.anyio
async def test_observability_logs_degraded(isolated_state: AppState):
    app = FastAPI()
    app.include_router(observability.router, prefix="/api")

    async def _missing_context():
        raise HTTPException(status_code=503, detail="Universe context unavailable; runtime not fully initialized")

    app.dependency_overrides[get_safe_universe_context] = _missing_context

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/observability/logs")
    assert response.status_code == 503
    assert response.json()["detail"] == "Universe context unavailable; runtime not fully initialized"


def test_lifespan_rebuild_error_branch():
    state = AppState()

    def boom(_universe):
        raise RuntimeError("rebuild failed")

    with pytest.raises(RuntimeError, match="rebuild failed"):
        state.rebuild_for_universe(Universe.SIMULATION, broker_factory=boom)
