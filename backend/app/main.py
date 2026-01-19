"""
FastAPI application entry point.

InvestCTR API - Investment Portfolio Management Platform
"""

import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

import sentry_sdk

from app.api.router import api_router
from app.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis import close_redis
from app.core.sentry import init_sentry

logger = get_logger(__name__)

# =============================================================================
# OpenAPI Tags Metadata
# =============================================================================
TAGS_METADATA = [
    {
        "name": "accounts",
        "description": "**Investment Account Management**. Create and manage brokerage accounts "
        "(BTG, XP, etc.) for organizing your investments. Each account can hold multiple "
        "positions and track its own transaction history.",
    },
    {
        "name": "assets",
        "description": "**Asset Catalog and Management**. Search and manage financial instruments "
        "including stocks, ETFs, FIIs (Brazilian REITs), BDRs, bonds, and more. Assets are "
        "shared across all users and linked to market data providers.",
    },
    {
        "name": "transactions",
        "description": "**Transaction History and Management**. Record and manage all financial "
        "events including buy/sell orders, dividends, JCP (Interest on Equity), splits, "
        "subscriptions, and other corporate actions. Transactions automatically update positions.",
    },
    {
        "name": "positions",
        "description": "**Current Portfolio Positions**. View your holdings with real-time market "
        "data, unrealized P&L calculations, and position details. Supports filtering by account "
        "and asset type, with consolidated views across accounts.",
    },
    {
        "name": "documents",
        "description": "**Document Processing and Parsing**. Upload brokerage statements (PDF) and "
        "automatically extract transactions using Claude AI. Supports BTG, XP, and other "
        "Brazilian brokers. Documents are stored securely in Supabase Storage.",
    },
    {
        "name": "portfolio",
        "description": "**Portfolio Analytics and Summaries**. Get consolidated portfolio views, "
        "allocation charts, historical performance, and comprehensive P&L analysis. Includes "
        "breakdowns by asset type and account.",
    },
    {
        "name": "quotes",
        "description": "**Market Data and Price Quotes**. Sync and retrieve current and historical "
        "prices for assets. Data sourced from Yahoo Finance with Redis caching for performance.",
    },
    {
        "name": "fund",
        "description": "**Fund-Style Metrics**. Track your portfolio as a personal fund with NAV "
        "(Net Asset Value) calculation, share value tracking, and professional-grade performance "
        "analytics including returns, volatility, and drawdown metrics.",
    },
    {
        "name": "cash-flows",
        "description": "**Cash Flow Management**. Track deposits and withdrawals for accurate "
        "portfolio accounting. Cash flows affect share calculations in fund-style tracking.",
    },
    {
        "name": "health",
        "description": "**System Health and Status**. Check API availability and service status.",
    },
]

# =============================================================================
# OpenAPI Description
# =============================================================================
API_DESCRIPTION = """
# InvestCTR API

**Investment Portfolio Management Platform**

InvestCTR is a comprehensive investment tracking platform designed for Brazilian investors.
It provides tools to manage your portfolio across multiple brokerage accounts, track performance,
and analyze your investments using fund-style metrics.

## Key Features

- **Multi-Account Support**: Manage investments across BTG, XP, and other brokers
- **AI-Powered Document Parsing**: Upload brokerage statements and automatically extract transactions
- **Real-Time Market Data**: Integrated with Yahoo Finance for current prices
- **Fund-Style Analytics**: Track your portfolio as a personal fund with NAV and share value
- **Comprehensive P&L**: Both realized and unrealized profit/loss calculations

## Authentication

All endpoints (except `/health`) require authentication via Supabase JWT tokens.
Include the token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

## Rate Limiting

API requests are rate-limited to 100 requests per minute per IP address.
Specific endpoints may have additional limits.

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "status_code": 400
}
```

Common error codes:
- `AUTHENTICATION_ERROR`: Invalid or missing authentication token
- `VALIDATION_ERROR`: Request validation failed
- `NOT_FOUND`: Requested resource not found
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Server-side error
"""


def is_origin_allowed(origin: str, allowed_origins: list[str]) -> bool:
    """Check if origin matches any allowed pattern (supports wildcards)."""
    if not origin:
        return False
    for pattern in allowed_origins:
        # Exact match
        if origin == pattern:
            return True
        # Wildcard pattern match (e.g., https://*.vercel.app)
        if "*" in pattern:
            regex_pattern = pattern.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{regex_pattern}$", origin):
                return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()

    # Initialize Sentry for error monitoring (before other services)
    sentry_initialized = init_sentry()
    if sentry_initialized:
        logger.info("sentry_initialized", environment=settings.environment)

    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    yield

    # Shutdown
    await close_redis()
    logger.info("application_shutdown")


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json"
        if settings.is_development
        else None,
        docs_url=f"{settings.api_v1_prefix}/docs" if settings.is_development else None,
        redoc_url=f"{settings.api_v1_prefix}/redoc"
        if settings.is_development
        else None,
        lifespan=lifespan,
        openapi_tags=TAGS_METADATA,
        contact={
            "name": "InvestCTR Team",
            "email": "support@investctr.com",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://investctr.com/terms",
        },
    )

    # Server error middleware with CORS support
    # This must be added BEFORE CORSMiddleware to ensure CORS headers
    # are included even on 500 errors (known FastAPI/Starlette issue)
    async def server_error_handler(request: Request, exc: Exception):
        """Handle server errors with CORS headers (middleware-level fallback)."""
        origin = request.headers.get("origin", "")
        # Only allow configured origins (with wildcard support)
        if not is_origin_allowed(origin, settings.cors_origins):
            origin = settings.cors_origins[0] if settings.cors_origins else "*"

        # Capture exception in Sentry
        sentry_sdk.capture_exception(exc)

        logger.exception(
            "server_error_middleware",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
        )
        content = {
            "detail": "Internal server error",
            "code": "INTERNAL_ERROR",
            "status_code": 500,
        }
        if not settings.is_production:
            content["details"] = {"error": str(exc), "type": type(exc).__name__}

        return JSONResponse(
            status_code=500,
            content=content,
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
            },
        )

    app.add_middleware(ServerErrorMiddleware, handler=server_error_handler)

    # Custom CORS middleware with wildcard support for Vercel previews
    class WildcardCORSMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            origin = request.headers.get("origin", "")

            # Handle preflight OPTIONS requests
            if request.method == "OPTIONS":
                if is_origin_allowed(origin, settings.cors_origins):
                    return JSONResponse(
                        content={},
                        headers={
                            "Access-Control-Allow-Origin": origin,
                            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                            "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
                            "Access-Control-Allow-Credentials": "true",
                            "Access-Control-Max-Age": "600",
                        },
                    )
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CORS not allowed",
                        "code": "CORS_ERROR",
                        "status_code": 403,
                    },
                )

            # Handle regular requests
            response = await call_next(request)

            if is_origin_allowed(origin, settings.cors_origins):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"

            return response

    app.add_middleware(WildcardCORSMiddleware)

    # Request logging middleware (runs after CORS, logs all requests)
    # This adds request_id to all logs and tracks request/response timing
    app.add_middleware(RequestLoggingMiddleware)

    # Global rate limiting middleware
    # Default: 100 requests/minute per IP for all endpoints
    # Specific endpoints use @rate_limit decorator for custom limits
    app.add_middleware(
        RateLimitMiddleware,
        requests=100,
        window=60,
        exclude_paths=[
            "/health",
            f"{settings.api_v1_prefix}/docs",
            f"{settings.api_v1_prefix}/redoc",
            f"{settings.api_v1_prefix}/openapi.json",
        ],
    )

    # Register all global exception handlers
    # This centralizes error handling with consistent response format:
    # {"detail": "message", "code": "ERROR_CODE", "status_code": 400}
    register_exception_handlers(app, is_origin_allowed)

    # Health check endpoint (outside of versioned API prefix)
    @app.get(
        "/health",
        tags=["health"],
        summary="Health Check",
        description="Check the health status of the API and its dependencies.",
        response_description="Health status of the API and dependent services",
        responses={
            200: {
                "description": "API is healthy",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "healthy",
                            "version": "0.1.0",
                            "environment": "production",
                            "services": {"redis": "up"},
                        }
                    }
                },
            }
        },
    )
    async def health_check() -> dict:
        """
        Health check endpoint for load balancers and monitoring.

        Returns the current status of the API and its dependent services:
        - **status**: Overall health status (healthy/unhealthy)
        - **version**: Current API version
        - **environment**: Deployment environment (development/staging/production)
        - **services**: Status of dependent services (Redis, etc.)
        """
        import asyncio

        from app.core.redis import redis_health_check

        # Try Redis health check with timeout, don't fail if Redis unavailable
        redis_ok = False
        try:
            redis_ok = await asyncio.wait_for(redis_health_check(), timeout=2.0)
        except Exception:
            pass  # Redis not available, but app is still healthy

        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "services": {
                "redis": "up" if redis_ok else "down",
            },
        }

    # Include API routes
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_application()
