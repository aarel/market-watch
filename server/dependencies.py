"""Shared FastAPI dependencies."""
from fastapi import Depends, HTTPException

import config
from broker import AlpacaBroker
from fake_broker import FakeBroker
from analytics.store import AnalyticsStore
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
