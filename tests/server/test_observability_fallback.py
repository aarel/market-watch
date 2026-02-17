from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
import httpx
import pytest

from server.routers import observability
from server.runtime.demo_hardening import get_safe_universe_context
from universe import Universe


@pytest.mark.anyio
async def test_observability_logs_returns_empty_when_log_missing(monkeypatch):
    app = FastAPI()
    app.include_router(observability.router, prefix="/api")

    ctx = SimpleNamespace(universe=Universe.SIMULATION)

    async def _ctx():
        return ctx

    app.dependency_overrides[get_safe_universe_context] = _ctx
    monkeypatch.setattr(observability, "get_system_log_path", lambda *_args, **_kwargs: "/tmp/not-a-real-log.jsonl")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/observability/logs")

    assert response.status_code == 200
    assert response.json() == {"logs": []}
