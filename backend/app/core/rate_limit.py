"""
Rate limiting implementation using Redis as backend.

Provides flexible rate limiting with:
- Per-endpoint/group limits
- Decorator-based API
- Standard rate limit headers (X-RateLimit-*)
- Graceful fallback when Redis is unavailable
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Request, Response
from starlette.responses import JSONResponse

from app.core.logging import get_logger
from app.core.redis import get_redis

logger = get_logger(__name__)


# Default rate limits by group
RATE_LIMITS = {
    "default": {"requests": 100, "window": 60},  # 100 requests/minute
    "upload": {"requests": 10, "window": 60},  # 10 uploads/minute
    "parse": {"requests": 5, "window": 60},  # 5 parse requests/minute (Claude API)
    "sync": {"requests": 10, "window": 60},  # 10 sync requests/minute
    "auth": {"requests": 20, "window": 60},  # 20 auth attempts/minute
}


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
    # Check for forwarded headers (reverse proxy scenario)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Uses Redis sorted sets for accurate sliding window rate limiting.
    Falls back gracefully (allows requests) when Redis is unavailable.
    """

    def __init__(self, prefix: str = "ratelimit"):
        self.prefix = prefix

    def _make_key(self, identifier: str, group: str = "default") -> str:
        """Generate Redis key for rate limit tracking."""
        return f"{self.prefix}:{group}:{identifier}"

    async def is_allowed(
        self,
        identifier: str,
        requests: int = 100,
        window: int = 60,
        group: str = "default",
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is allowed under rate limit.

        Uses sliding window log algorithm with Redis sorted sets.

        Args:
            identifier: Unique identifier (usually IP or user ID)
            requests: Maximum requests allowed in window
            window: Time window in seconds
            group: Rate limit group name

        Returns:
            tuple of (is_allowed, rate_limit_info)
            rate_limit_info contains: limit, remaining, reset
        """
        try:
            redis = await get_redis()
            key = self._make_key(identifier, group)
            now = time.time()
            window_start = now - window

            # Use pipeline for atomic operations
            pipe = redis.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request (we'll remove if over limit)
            pipe.zadd(key, {str(now): now})

            # Set expiry on the key
            pipe.expire(key, window)

            results = await pipe.execute()
            current_count = results[1]

            # Calculate remaining and reset time
            remaining = max(0, requests - current_count - 1)
            reset_at = int(now + window)

            rate_info = {
                "limit": requests,
                "remaining": remaining,
                "reset": reset_at,
            }

            if current_count >= requests:
                # Over limit - remove the request we just added
                await redis.zrem(key, str(now))
                rate_info["remaining"] = 0
                return False, rate_info

            return True, rate_info

        except Exception as e:
            # Redis unavailable - gracefully allow request
            logger.warning(
                "rate_limit_redis_error",
                error=str(e),
                identifier=identifier,
                group=group,
            )
            # Return permissive defaults when Redis is down
            return True, {
                "limit": requests,
                "remaining": requests - 1,
                "reset": int(time.time() + window),
            }

    async def get_remaining(
        self,
        identifier: str,
        requests: int = 100,
        window: int = 60,
        group: str = "default",
    ) -> dict[str, int]:
        """
        Get current rate limit status without consuming a request.

        Returns:
            dict with limit, remaining, reset values
        """
        try:
            redis = await get_redis()
            key = self._make_key(identifier, group)
            now = time.time()
            window_start = now - window

            # Remove old entries and count
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()

            current_count = results[1]
            remaining = max(0, requests - current_count)

            return {
                "limit": requests,
                "remaining": remaining,
                "reset": int(now + window),
            }

        except Exception as e:
            logger.warning(
                "rate_limit_status_error",
                error=str(e),
                identifier=identifier,
            )
            return {
                "limit": requests,
                "remaining": requests,
                "reset": int(time.time() + window),
            }

    async def reset(self, identifier: str, group: str = "default") -> bool:
        """Reset rate limit for an identifier."""
        try:
            redis = await get_redis()
            key = self._make_key(identifier, group)
            await redis.delete(key)
            return True
        except Exception as e:
            logger.warning(
                "rate_limit_reset_error",
                error=str(e),
                identifier=identifier,
            )
            return False


# Global rate limiter instance
rate_limiter = RateLimiter()


def add_rate_limit_headers(response: Response, rate_info: dict[str, int]) -> None:
    """Add standard rate limit headers to response."""
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])


def rate_limit(
    requests: int | None = None,
    window: int | None = None,
    group: str = "default",
    key_func: Callable[[Request], str] | None = None,
) -> Callable:
    """
    Rate limiting decorator for FastAPI endpoints.

    Usage:
        @router.get("/endpoint")
        @rate_limit(requests=10, window=60, group="upload")
        async def my_endpoint(request: Request):
            ...

    Args:
        requests: Max requests allowed (defaults to group config)
        window: Time window in seconds (defaults to group config)
        group: Rate limit group name for defaults
        key_func: Custom function to extract identifier from request

    Note:
        The decorated function MUST have a `request: Request` parameter.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract request from kwargs or args
            request: Request | None = kwargs.get("request")
            if request is None:
                # Try to find Request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request is None:
                # No request found - just call the function
                logger.warning(
                    "rate_limit_no_request",
                    function=func.__name__,
                )
                return await func(*args, **kwargs)

            # Get rate limit config
            config = RATE_LIMITS.get(group, RATE_LIMITS["default"])
            max_requests = requests if requests is not None else config["requests"]
            time_window = window if window is not None else config["window"]

            # Extract identifier
            if key_func:
                identifier = key_func(request)
            else:
                identifier = get_client_ip(request)

            # Check rate limit
            allowed, rate_info = await rate_limiter.is_allowed(
                identifier=identifier,
                requests=max_requests,
                window=time_window,
                group=group,
            )

            if not allowed:
                logger.warning(
                    "rate_limit_exceeded",
                    identifier=identifier,
                    group=group,
                    path=str(request.url.path),
                )
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "details": {
                            "limit": rate_info["limit"],
                            "window": time_window,
                            "retry_after": rate_info["reset"] - int(time.time()),
                        },
                    },
                )
                add_rate_limit_headers(response, rate_info)
                response.headers["Retry-After"] = str(
                    rate_info["reset"] - int(time.time())
                )
                return response

            # Call the actual function
            result = await func(*args, **kwargs)

            # Add rate limit headers to response if possible
            if isinstance(result, Response):
                add_rate_limit_headers(result, rate_info)

            return result

        return wrapper

    return decorator


class RateLimitMiddleware:
    """
    ASGI Middleware for global rate limiting.

    Applies default rate limits to all requests.
    Specific endpoints can use the @rate_limit decorator for custom limits.
    """

    def __init__(
        self,
        app: Any,
        requests: int = 100,
        window: int = 60,
        exclude_paths: list[str] | None = None,
    ):
        self.app = app
        self.requests = requests
        self.window = window
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        path = request.url.path

        # Skip rate limiting for excluded paths
        for exclude in self.exclude_paths:
            if path.startswith(exclude) or path == exclude:
                await self.app(scope, receive, send)
                return

        # Skip OPTIONS (preflight) requests
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        identifier = get_client_ip(request)

        allowed, rate_info = await rate_limiter.is_allowed(
            identifier=identifier,
            requests=self.requests,
            window=self.window,
            group="global",
        )

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "details": {
                        "limit": rate_info["limit"],
                        "window": self.window,
                        "retry_after": rate_info["reset"] - int(time.time()),
                    },
                },
            )
            add_rate_limit_headers(response, rate_info)
            response.headers["Retry-After"] = str(rate_info["reset"] - int(time.time()))

            await response(scope, receive, send)
            return

        # Store rate info for use by endpoints
        scope["state"] = (
            getattr(scope.get("state"), "__dict__", {}) if scope.get("state") else {}
        )
        scope["rate_limit_info"] = rate_info

        # Wrap send to add headers to response
        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-ratelimit-limit", str(rate_info["limit"]).encode()))
                headers.append(
                    (b"x-ratelimit-remaining", str(rate_info["remaining"]).encode())
                )
                headers.append((b"x-ratelimit-reset", str(rate_info["reset"]).encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


def get_user_identifier(request: Request) -> str:
    """
    Extract user identifier for rate limiting.

    Prefers authenticated user ID, falls back to IP address.
    Use this as key_func for user-based rate limiting.
    """
    # Check if user is attached to request state
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"
    return f"ip:{get_client_ip(request)}"
