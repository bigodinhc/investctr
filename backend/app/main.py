"""
FastAPI application entry point.
"""

import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

from app.api.router import api_router
from app.config import settings
from app.core.exceptions import AppException, AuthenticationError
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis, redis_health_check

logger = get_logger(__name__)


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
        description="Investment portfolio management platform API",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json"
        if settings.is_development
        else None,
        docs_url=f"{settings.api_v1_prefix}/docs" if settings.is_development else None,
        redoc_url=f"{settings.api_v1_prefix}/redoc"
        if settings.is_development
        else None,
        lifespan=lifespan,
    )

    # Server error middleware with CORS support
    # This must be added BEFORE CORSMiddleware to ensure CORS headers
    # are included even on 500 errors (known FastAPI/Starlette issue)
    async def server_error_handler(request: Request, exc: Exception):
        """Handle server errors with CORS headers."""
        origin = request.headers.get("origin", "")
        # Only allow configured origins (with wildcard support)
        if not is_origin_allowed(origin, settings.cors_origins):
            origin = settings.cors_origins[0] if settings.cors_origins else "*"

        logger.exception(
            "server_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "details": {} if settings.is_production else {"message": str(exc)},
            },
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
                    status_code=403, content={"error": "CORS not allowed"}
                )

            # Handle regular requests
            response = await call_next(request)

            if is_origin_allowed(origin, settings.cors_origins):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"

            return response

    app.add_middleware(WildcardCORSMiddleware)

    # Exception handlers
    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors with proper WWW-Authenticate header."""
        logger.warning(
            "authentication_failed",
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "app_exception",
            status_code=exc.status_code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(OperationalError)
    async def database_operational_error_handler(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        """Handle database connection/operational errors."""
        logger.error(
            "database_operational_error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database temporarily unavailable",
                "details": {} if settings.is_production else {"message": str(exc)},
            },
        )

    @app.exception_handler(DBAPIError)
    async def database_api_error_handler(
        request: Request, exc: DBAPIError
    ) -> JSONResponse:
        """Handle database API errors."""
        logger.error(
            "database_api_error",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "Database error",
                "details": {} if settings.is_production else {"message": str(exc)},
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "details": {} if settings.is_production else {"message": str(exc)},
            },
        )

    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check() -> dict:
        """Health check endpoint."""
        # Try Redis health check with timeout, don't fail if Redis unavailable
        redis_ok = False
        try:
            import asyncio

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
