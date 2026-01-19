"""
Request logging middleware for structured logging.

Provides:
- Automatic request_id generation and propagation
- Request/response logging with timing
- User context extraction from JWT
- Correlation ID in response headers
"""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import (
    clear_log_context,
    clear_request_context,
    generate_request_id,
    get_logger,
    set_request_context,
)

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses with context.

    Features:
    - Generates unique request_id for each request (correlation ID)
    - Logs request entry with method, path, and user_id (if authenticated)
    - Logs response with status_code and duration_ms
    - Adds X-Request-ID header to responses
    - Cleans up context after request completes
    """

    # Paths to exclude from detailed logging (health checks, etc.)
    EXCLUDE_PATHS = {"/health", "/metrics", "/favicon.ico"}

    # Paths to log at debug level instead of info
    DEBUG_PATHS = {"/api/v1/docs", "/api/v1/openapi.json", "/api/v1/redoc"}

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging context."""
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        # Generate or extract request_id
        request_id = request.headers.get("X-Request-ID") or generate_request_id()

        # Extract user_id from request state if available (set by auth dependency)
        # This will be None initially; auth dependency may set it later
        user_id = getattr(request.state, "user_id", None)

        # Set request context for all logs during this request
        set_request_context(request_id=request_id, user_id=user_id)

        # Determine log level based on path
        is_debug_path = request.url.path in self.DEBUG_PATHS
        log_func = logger.debug if is_debug_path else logger.info

        # Log request entry
        log_func(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_string=str(request.query_params) if request.query_params else None,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        # Process request and measure duration
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception (will be re-raised and handled by exception handlers)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "request_exception",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            raise
        finally:
            # Clean up context
            clear_request_context()
            clear_log_context()

        # Calculate request duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add correlation header to response
        response.headers["X-Request-ID"] = request_id

        # Update user_id if it was set during request processing
        user_id = getattr(request.state, "user_id", None)

        # Log response with timing
        log_data = {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }

        # Add user_id if available
        if user_id:
            log_data["user_id"] = user_id

        # Use appropriate log level based on status code
        if response.status_code >= 500:
            logger.error("request_completed", **log_data)
        elif response.status_code >= 400:
            logger.warning("request_completed", **log_data)
        else:
            log_func("request_completed", **log_data)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, considering proxies."""
        # Check for forwarded headers (from reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # First IP in the list is the original client
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"


class UserContextMiddleware(BaseHTTPMiddleware):
    """Middleware to capture user_id from authenticated requests.

    This middleware runs after authentication and captures the user_id
    from request.state to include it in subsequent log messages.

    Should be added AFTER authentication middleware/dependency runs.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Capture user context if available."""
        response = await call_next(request)

        # If user_id was set during request (by auth dependency),
        # ensure it's in the logging context for any remaining logs
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            set_request_context(user_id=user_id)

        return response
