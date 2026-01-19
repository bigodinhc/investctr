"""
Global exception handlers for the FastAPI application.

Provides consistent error response format:
{
    "detail": "Human-readable error message",
    "code": "ERROR_CODE",
    "status_code": 400
}
"""

from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, SQLAlchemyError

from app.config import settings
from app.core.exceptions import AppException, AuthenticationError, RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_cors_headers(request: Request, is_origin_allowed: Callable[[str, list[str]], bool]) -> dict[str, str]:
    """Get CORS headers for error responses."""
    origin = request.headers.get("origin", "")
    headers = {}

    if origin and is_origin_allowed(origin, settings.cors_origins):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return headers


def create_error_response(
    status_code: int,
    detail: str,
    code: str,
    request: Request,
    is_origin_allowed: Callable[[str, list[str]], bool],
    extra_headers: dict[str, str] | None = None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a standardized error response with CORS headers."""
    content = {
        "detail": detail,
        "code": code,
        "status_code": status_code,
    }

    if details:
        content["details"] = details

    headers = get_cors_headers(request, is_origin_allowed)
    if extra_headers:
        headers.update(extra_headers)

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers if headers else None,
    )


def register_exception_handlers(app: FastAPI, is_origin_allowed: Callable[[str, list[str]], bool]) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(RateLimitError)
    async def rate_limit_error_handler(
        request: Request, exc: RateLimitError
    ) -> JSONResponse:
        """Handle rate limit errors."""
        logger.warning(
            "rate_limit_exceeded",
            message=exc.message,
            code=exc.code,
            path=request.url.path,
        )
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.message,
            code=exc.code,
            request=request,
            is_origin_allowed=is_origin_allowed,
            details=exc.details if exc.details else None,
        )

    @app.exception_handler(AuthenticationError)
    async def authentication_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        """Handle authentication errors with proper WWW-Authenticate header and CORS."""
        logger.warning(
            "authentication_failed",
            message=exc.message,
            code=exc.code,
            path=request.url.path,
        )
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.message,
            code=exc.code,
            request=request,
            is_origin_allowed=is_origin_allowed,
            extra_headers={"WWW-Authenticate": "Bearer"},
            details=exc.details if exc.details else None,
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        logger.warning(
            "app_exception",
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            path=request.url.path,
        )
        return create_error_response(
            status_code=exc.status_code,
            detail=exc.message,
            code=exc.code,
            request=request,
            is_origin_allowed=is_origin_allowed,
            details=exc.details if exc.details else None,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle FastAPI request validation errors (body, query, path params)."""
        errors = exc.errors()
        # Format validation errors for better readability
        formatted_errors = []
        for error in errors:
            loc = " -> ".join(str(part) for part in error.get("loc", []))
            formatted_errors.append({
                "field": loc,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            })

        logger.warning(
            "request_validation_error",
            path=request.url.path,
            errors=formatted_errors,
        )

        return create_error_response(
            status_code=422,
            detail="Request validation failed",
            code="VALIDATION_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"errors": formatted_errors},
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors (from manual validation)."""
        errors = exc.errors()
        formatted_errors = []
        for error in errors:
            loc = " -> ".join(str(part) for part in error.get("loc", []))
            formatted_errors.append({
                "field": loc,
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            })

        logger.warning(
            "pydantic_validation_error",
            path=request.url.path,
            errors=formatted_errors,
        )

        return create_error_response(
            status_code=422,
            detail="Data validation failed",
            code="VALIDATION_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"errors": formatted_errors},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """Handle standard FastAPI HTTPException."""
        # Map common HTTP status codes to error codes
        code_mapping = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            408: "REQUEST_TIMEOUT",
            409: "CONFLICT",
            410: "GONE",
            422: "UNPROCESSABLE_ENTITY",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
            502: "BAD_GATEWAY",
            503: "SERVICE_UNAVAILABLE",
            504: "GATEWAY_TIMEOUT",
        }

        error_code = code_mapping.get(exc.status_code, f"HTTP_{exc.status_code}")

        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            code=error_code,
            detail=exc.detail,
            path=request.url.path,
        )

        extra_headers = {}
        if exc.headers:
            extra_headers.update(exc.headers)

        return create_error_response(
            status_code=exc.status_code,
            detail=str(exc.detail) if exc.detail else "An error occurred",
            code=error_code,
            request=request,
            is_origin_allowed=is_origin_allowed,
            extra_headers=extra_headers if extra_headers else None,
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """Handle database integrity constraint violations."""
        logger.error(
            "database_integrity_error",
            error=str(exc),
            path=request.url.path,
        )

        # Try to extract useful info from the error
        detail = "Database integrity constraint violated"
        if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
            detail = "A record with this data already exists"
        elif "foreign key" in str(exc).lower():
            detail = "Referenced record does not exist"
        elif "not null" in str(exc).lower():
            detail = "Required field is missing"

        return create_error_response(
            status_code=409,
            detail=detail,
            code="DATABASE_INTEGRITY_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"error": str(exc)} if not settings.is_production else None,
        )

    @app.exception_handler(OperationalError)
    async def operational_error_handler(
        request: Request, exc: OperationalError
    ) -> JSONResponse:
        """Handle database connection/operational errors."""
        logger.error(
            "database_operational_error",
            error=str(exc),
            path=request.url.path,
        )

        return create_error_response(
            status_code=503,
            detail="Database temporarily unavailable",
            code="DATABASE_UNAVAILABLE",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"error": str(exc)} if not settings.is_production else None,
        )

    @app.exception_handler(DBAPIError)
    async def dbapi_error_handler(
        request: Request, exc: DBAPIError
    ) -> JSONResponse:
        """Handle database API errors."""
        logger.error(
            "database_api_error",
            error=str(exc),
            path=request.url.path,
        )

        return create_error_response(
            status_code=503,
            detail="Database error",
            code="DATABASE_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"error": str(exc)} if not settings.is_production else None,
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle general SQLAlchemy errors."""
        logger.error(
            "sqlalchemy_error",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
        )

        return create_error_response(
            status_code=500,
            detail="Database operation failed",
            code="DATABASE_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"error": str(exc)} if not settings.is_production else None,
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions (catch-all)."""
        logger.exception(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=request.url.path,
        )

        return create_error_response(
            status_code=500,
            detail="Internal server error",
            code="INTERNAL_ERROR",
            request=request,
            is_origin_allowed=is_origin_allowed,
            details={"error": str(exc), "type": type(exc).__name__} if not settings.is_production else None,
        )
