"""Shared FastAPI dependencies."""
from fastapi import Depends, HTTPException
from starlette.requests import Request

import config

from .config_manager import ConfigManager
from .state import AppState


def get_state() -> AppState:
    return AppState.instance()


def get_config_manager(state: AppState = Depends(get_state)) -> ConfigManager:
    return state.config_manager


def get_broker(state: AppState = Depends(get_state)):
    if not state.broker:
        raise HTTPException(status_code=503, detail="Broker not initialized")
    return state.broker


def get_analytics_store(state: AppState = Depends(get_state)):
    if not config.ANALYTICS_ENABLED or not state.analytics_store:
        raise HTTPException(status_code=503, detail="Analytics is disabled")
    return state.analytics_store


def require_api_access(request: Request) -> None:
    """Gate all API routes behind an optional token + origin check.

    When API_TOKEN is set in the environment, every request must supply a
    matching X-Api-Key header.  When API_TOKEN is empty the gate falls back
    to an IP allowlist (localhost only), which is safe when uvicorn is
    fronted by a local nginx proxy but should not be used in place of a
    real token for any publicly reachable service.
    """
    api_token = getattr(config, "API_TOKEN", "")
    allowed_origins = getattr(config, "ALLOWED_ORIGINS", [])
    client_ip = request.client.host if request.client else None
    origin = request.headers.get("origin")
    provided = request.headers.get("x-api-key")

    if not api_token:
        if origin and allowed_origins and origin not in allowed_origins:
            raise HTTPException(status_code=403, detail="Origin not allowed")
        if client_ip not in ("127.0.0.1", "::1"):
            raise HTTPException(status_code=403, detail="Forbidden")
        return

    if provided != api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if origin and allowed_origins and origin not in allowed_origins:
        raise HTTPException(status_code=403, detail="Origin not allowed")
