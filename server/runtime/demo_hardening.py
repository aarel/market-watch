"""Demo reliability hardening for partial-startup environments.

This module adds safe dependency guards and startup diagnostics without
changing core business logic.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from server.dependencies import get_config_manager, get_state

logger = logging.getLogger(__name__)


def _missing_state_fields(state) -> list[str]:
    missing: list[str] = []
    if getattr(state, "config_manager", None) is None:
        missing.append("config_manager")
    ctx = getattr(state, "universe_context", None)
    if ctx is None:
        missing.append("universe_context")
    elif getattr(ctx, "universe", None) is None:
        missing.append("universe_context.universe")
    return missing


def get_safe_config_manager(state=Depends(get_state)):
    cfg = getattr(state, "config_manager", None)
    if cfg is None:
        logger.warning("Demo hardening: config manager missing; returning controlled 503")
        raise HTTPException(status_code=503, detail="Config manager unavailable; runtime not fully initialized")
    return cfg


def get_safe_universe_context(state=Depends(get_state)):
    ctx = getattr(state, "universe_context", None)
    if ctx is None or getattr(ctx, "universe", None) is None:
        logger.warning("Demo hardening: universe context missing; returning controlled 503")
        raise HTTPException(status_code=503, detail="Universe context unavailable; runtime not fully initialized")
    return ctx


def get_safe_state_for_observability(state=Depends(get_state)):
    # Keep observability router signatures unchanged while enforcing a safe boundary.
    _ = get_safe_universe_context(state)
    return state


def _iter_dependant_tree(dependant):
    for dep in getattr(dependant, "dependencies", []):
        yield dep
        yield from _iter_dependant_tree(dep)


def _apply_substitutions(app: FastAPI) -> int:
    substitutions = 0

    # Optional import for future-proof replacement if a direct dependency exists.
    get_universe_context: Callable | None = None
    try:
        from server.dependencies import get_universe_context as _guc  # type: ignore

        get_universe_context = _guc
    except Exception:
        get_universe_context = None

    for route in app.router.routes:
        if not isinstance(route, APIRoute):
            continue

        for dep in _iter_dependant_tree(route.dependant):
            if dep.call is get_config_manager:
                dep.call = get_safe_config_manager
                substitutions += 1
                logger.info("Demo hardening substitution: %s %s -> get_safe_config_manager", route.methods, route.path)
            elif get_universe_context is not None and dep.call is get_universe_context:
                dep.call = get_safe_universe_context
                substitutions += 1
                logger.info("Demo hardening substitution: %s %s -> get_safe_universe_context", route.methods, route.path)
            elif route.path == "/api/observability/logs" and dep.call is get_state:
                dep.call = get_safe_state_for_observability
                substitutions += 1
                logger.info(
                    "Demo hardening substitution: %s %s get_state -> get_safe_state_for_observability",
                    route.methods,
                    route.path,
                )

    # Add overrides too, so any late-bound dependency resolution is consistent.
    app.dependency_overrides[get_config_manager] = get_safe_config_manager
    if get_universe_context is not None:
        app.dependency_overrides[get_universe_context] = get_safe_universe_context

    return substitutions


def _build_health_router() -> APIRouter:
    router = APIRouter(tags=["demo-hardening"])

    @router.get("/health")
    async def health(state=Depends(get_state)):
        missing = _missing_state_fields(state)
        if missing:
            payload = {"status": "unhealthy", "missing": missing}
            return JSONResponse(status_code=503, content=payload)
        return {"status": "healthy"}

    return router


def build_demo_hardening(app: FastAPI) -> None:
    app.include_router(_build_health_router())
    count = _apply_substitutions(app)
    logger.info("Demo hardening initialized; dependency substitutions=%s", count)

    @app.on_event("startup")
    async def _demo_hardening_startup_probe() -> None:
        if os.getenv("FASTAPI_DISABLE_LIFESPAN", "0") == "1":
            logger.warning(
                "FASTAPI_DISABLE_LIFESPAN=1 detected; runtime may start in degraded mode. "
                "Demo hardening will return controlled 503 responses for missing dependencies."
            )

        state = get_state()
        missing = _missing_state_fields(state)
        if missing:
            logger.warning("Demo hardening startup probe: missing runtime state fields=%s", missing)
        else:
            logger.info("Demo hardening startup probe: runtime readiness fields present")
