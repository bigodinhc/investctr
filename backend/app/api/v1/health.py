"""
Health check endpoints for monitoring and orchestration.

These endpoints are used by:
- Kubernetes/Railway for liveness and readiness probes
- Load balancers for health monitoring
- Monitoring systems for alerting

All endpoints are public (no authentication required).
"""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceCheck(BaseModel):
    """Individual service check result."""

    status: str  # "up" or "down"
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", or "unhealthy"
    timestamp: str
    version: str
    environment: str | None = None
    checks: dict[str, ServiceCheck] | None = None


router = APIRouter(prefix="/health", tags=["health"])


async def check_database() -> ServiceCheck:
    """Check database connectivity and measure latency."""
    try:
        from app.database import get_session_maker

        start = time.perf_counter()
        session_maker = get_session_maker()
        async with session_maker() as session:
            await session.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        return ServiceCheck(status="up", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return ServiceCheck(status="down", error=str(e))


async def check_redis() -> ServiceCheck:
    """Check Redis connectivity and measure latency."""
    try:
        from app.core.redis import get_redis

        start = time.perf_counter()
        client = await get_redis()
        await client.ping()
        latency = (time.perf_counter() - start) * 1000  # Convert to ms

        return ServiceCheck(status="up", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return ServiceCheck(status="down", error=str(e))


def get_overall_status(checks: dict[str, ServiceCheck]) -> str:
    """
    Determine overall health status based on individual checks.

    - healthy: All services are up
    - degraded: Some non-critical services are down (e.g., Redis)
    - unhealthy: Critical services are down (e.g., database)
    """
    critical_services = ["database"]

    all_up = all(check.status == "up" for check in checks.values())
    if all_up:
        return "healthy"

    # Check if any critical service is down
    for service in critical_services:
        if service in checks and checks[service].status == "down":
            return "unhealthy"

    # Non-critical services are down
    return "degraded"


@router.get(
    "",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns 200 if the application is running. Used for basic uptime monitoring.",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Always returns 200 if the application is running.
    Does not check external dependencies.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the application is alive. Used by Kubernetes liveness probes.",
)
async def liveness_check() -> HealthResponse:
    """
    Liveness probe endpoint.

    Returns 200 if the application process is running and can handle requests.
    This should be a lightweight check that doesn't verify external dependencies.

    If this fails, the orchestrator should restart the container.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Checks if the application is ready to serve traffic. Verifies database and Redis connectivity.",
)
async def readiness_check() -> HealthResponse:
    """
    Readiness probe endpoint.

    Verifies that the application can serve traffic by checking:
    - Database connectivity (critical)
    - Redis connectivity (non-critical)

    Returns:
    - 200 with status "healthy" if all services are up
    - 200 with status "degraded" if non-critical services are down
    - 503 with status "unhealthy" if critical services are down
    """
    import asyncio

    # Run health checks concurrently with timeout
    try:
        db_check, redis_check = await asyncio.wait_for(
            asyncio.gather(
                check_database(),
                check_redis(),
                return_exceptions=True,
            ),
            timeout=10.0,  # 10 second timeout for all checks
        )

        # Handle exceptions from gather
        if isinstance(db_check, Exception):
            db_check = ServiceCheck(status="down", error=str(db_check))
        if isinstance(redis_check, Exception):
            redis_check = ServiceCheck(status="down", error=str(redis_check))

    except asyncio.TimeoutError:
        db_check = ServiceCheck(status="down", error="Health check timeout")
        redis_check = ServiceCheck(status="down", error="Health check timeout")

    checks = {
        "database": db_check,
        "redis": redis_check,
    }

    overall_status = get_overall_status(checks)

    response = HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.app_version,
        environment=settings.environment,
        checks=checks,
    )

    # Log if not healthy
    if overall_status != "healthy":
        logger.warning(
            "readiness_check_not_healthy",
            status=overall_status,
            checks={k: v.model_dump() for k, v in checks.items()},
        )

    return response
