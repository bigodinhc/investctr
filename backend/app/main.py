"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.redis import close_redis, redis_health_check

logger = get_logger(__name__)


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
        redoc_url=f"{settings.api_v1_prefix}/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
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

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
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
