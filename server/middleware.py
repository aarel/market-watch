"""
Middleware for API request tracking.

Includes latency tracking middleware that measures request duration
and records it for monitoring purposes.
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .latency_tracker import get_tracker


class LatencyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track request latency.

    Measures duration of each request and records it with the latency tracker.
    Only tracks API endpoints (excludes static files, websockets).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and measure duration.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response from handler
        """
        # Only track API endpoints (skip static files, websockets)
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        # Measure request duration
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            return response
        finally:
            # Record latency (even if request failed)
            duration_ms = (time.perf_counter() - start_time) * 1000
            tracker = get_tracker()
            tracker.record(path, duration_ms)
