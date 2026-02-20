"""Demo mode enforcement — blocks all state-changing operations server-side.

When MARKET_WATCH_DEMO_MODE=1, all POST/PUT/PATCH/DELETE requests are blocked with 403 unless
explicitly allowlisted. This ensures demo users can browse the UI but cannot
modify state, execute trades, or change configuration.
"""
import os
from typing import Set

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


# Environment flag
DEMO_MODE_ENABLED = os.getenv("MARKET_WATCH_DEMO_MODE", "0").lower() in {"1", "true", "yes", "on"}

# Allowlisted paths that can accept writes even in demo mode
# (e.g., health checks, read-only endpoints mistakenly using POST)
DEMO_MODE_ALLOWLIST: Set[str] = {
    "/api/health",  # Health check (if it were POST)
    # Add other safe paths here if needed
}


class DemoModeMiddleware(BaseHTTPMiddleware):
    """Middleware to block all write operations in demo mode.

    Applies to POST, PUT, PATCH, DELETE methods except for allowlisted paths.
    Returns 403 with a clear message when blocked.
    """

    async def dispatch(self, request: Request, call_next):
        if not DEMO_MODE_ENABLED:
            # Demo mode off — pass through
            return await call_next(request)

        # Block write methods unless allowlisted
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.url.path not in DEMO_MODE_ALLOWLIST:
                return Response(
                    content='{"detail":"Demo mode: state-changing operations are disabled"}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


def require_demo_mode_disabled(request: Request) -> None:
    """FastAPI dependency to block endpoints entirely in demo mode.

    Use this on critical write endpoints that should not even attempt
    processing in demo mode (e.g., trade execution, config changes).

    Usage:
        @router.post("/api/trades", dependencies=[Depends(require_demo_mode_disabled)])
        async def create_trade(...):
            ...
    """
    if DEMO_MODE_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Demo mode: this operation is disabled in demo environments"
        )


def is_demo_mode() -> bool:
    """Check if demo mode is currently enabled."""
    return DEMO_MODE_ENABLED
