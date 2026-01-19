"""
Custom exceptions for the application.

All exceptions follow a consistent error response format:
{
    "detail": "Human-readable error message",
    "code": "ERROR_CODE",
    "status_code": 400
}
"""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to response dictionary."""
        response = {
            "detail": self.message,
            "code": self.code,
            "status_code": self.status_code,
        }
        if self.details:
            response["details"] = self.details
        return response


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} not found",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ValidationError(AppException):
    """Validation error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
        )


class AuthorizationError(AppException):
    """Authorization failed."""

    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
        )


class ConflictError(AppException):
    """Resource conflict."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class ExternalServiceError(AppException):
    """External service error."""

    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"External service error: {service}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service, "error": message},
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
        )


class DatabaseError(AppException):
    """Database operation error."""

    def __init__(
        self, message: str = "Database error", details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=503,
            details=details,
        )


class BadRequestError(AppException):
    """Bad request error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=400,
            details=details,
        )
