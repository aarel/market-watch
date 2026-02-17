from __future__ import annotations

import importlib
from collections.abc import Iterator

import pytest

from server.state import AppState


def _reload_main(monkeypatch: pytest.MonkeyPatch, *, demo_mode: str, disable_lifespan: str):
    monkeypatch.setenv("MARKET_WATCH_DEMO_MODE", demo_mode)
    monkeypatch.setenv("FASTAPI_DISABLE_LIFESPAN", disable_lifespan)
    import server.main as server_main

    return importlib.reload(server_main)


@pytest.fixture
def isolated_state() -> Iterator[AppState]:
    state = AppState.instance()
    snapshot = {
        "broker": state.broker,
        "coordinator": state.coordinator,
        "error": state.error,
        "config_manager": state.config_manager,
        "universe_context": state.universe_context,
    }
    state.broker = None
    state.coordinator = None
    state.error = None
    state.config_manager = None
    state.universe_context = None
    try:
        yield state
    finally:
        for key, value in snapshot.items():
            setattr(state, key, value)


def test_noop_lifespan_selected(monkeypatch: pytest.MonkeyPatch):
    module = _reload_main(monkeypatch, demo_mode="0", disable_lifespan="1")
    assert module.SELECTED_LIFESPAN is module.noop_lifespan


def test_full_lifespan_initializer(monkeypatch: pytest.MonkeyPatch):
    module = _reload_main(monkeypatch, demo_mode="0", disable_lifespan="0")
    assert module.SELECTED_LIFESPAN is module.full_lifespan


def test_demo_mode_forces_full_lifespan(monkeypatch: pytest.MonkeyPatch):
    module = _reload_main(monkeypatch, demo_mode="1", disable_lifespan="1")
    assert module.SELECTED_LIFESPAN is module.full_lifespan


@pytest.mark.anyio
async def test_noop_lifespan_health_endpoint_reports_unhealthy(monkeypatch: pytest.MonkeyPatch, isolated_state: AppState):
    module = _reload_main(monkeypatch, demo_mode="0", disable_lifespan="1")
    assert module.SELECTED_LIFESPAN is module.noop_lifespan

    from server.routers import status

    response = await status.health(state=isolated_state)
    body = response.body.decode("utf-8")
    assert response.status_code == 503
    assert '"status":"unhealthy"' in body
    assert '"agents":{"status":"fail"' in body
    assert '"broker_api":{"status":"fail"' in body
