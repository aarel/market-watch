"""Server package entrypoint with legacy compatibility helpers for tests."""
from fastapi import HTTPException

import config

from .config_manager import ConfigManager
from .dependencies import require_api_access  # noqa: F401 — re-exported for tests/legacy callers
from .state import AppState

try:
    from .main import app  # noqa: F401
except ModuleNotFoundError:
    # Allow partial imports (for isolated tests/tools) when optional web deps
    # are unavailable in the current environment.
    app = None  # type: ignore[assignment]

# Expose shared state and config for tests and legacy imports
state = AppState.instance()
config_manager: ConfigManager = state.config_manager


# ---------------------------------------------------------------------------
# Legacy config persistence helpers (used by existing tests)
# ---------------------------------------------------------------------------
def load_config_state():
    """Load persisted config into the runtime config module."""
    config_manager.path = config.CONFIG_STATE_PATH
    config_manager.load()


def save_config_state():
    """Persist current config module values to disk."""
    config_manager.path = config.CONFIG_STATE_PATH
    config_manager.save()




# ---------------------------------------------------------------------------
# Risk breaker helper (legacy test entrypoint)
# ---------------------------------------------------------------------------
async def reset_risk_breaker():
    if not state.coordinator:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    breaker_status = state.coordinator.reset_circuit_breaker()
    return {"status": "ok", "breaker": breaker_status}


__all__ = [
    "app",
    "state",
    "config",
    "load_config_state",
    "save_config_state",
    "require_api_access",
    "reset_risk_breaker",
]
