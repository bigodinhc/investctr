"""
Base schemas and common utilities.
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    created_at: datetime
    updated_at: datetime | None = None


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    skip: int = 0
    limit: int = 50

    @property
    def has_more(self) -> bool:
        return self.skip + len(self.items) < self.total


class IDMixin(BaseModel):
    """Mixin for ID field."""

    id: UUID


# =============================================================================
# Error Response Schemas (for OpenAPI documentation)
# =============================================================================


class ErrorResponse(BaseSchema):
    """Standard error response format."""

    detail: str
    code: str
    status_code: int
    details: dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Resource not found",
                "code": "NOT_FOUND",
                "status_code": 404,
            }
        }


class ValidationErrorDetail(BaseSchema):
    """Validation error detail for a single field."""

    loc: list[str]
    msg: str
    type: str


class ValidationErrorResponse(BaseSchema):
    """Validation error response format (422)."""

    detail: list[ValidationErrorDetail]

    class Config:
        json_schema_extra = {
            "example": {
                "detail": [
                    {
                        "loc": ["body", "name"],
                        "msg": "field required",
                        "type": "value_error.missing",
                    }
                ]
            }
        }


# Common response definitions for reuse in endpoint decorators
COMMON_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid input data",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid request data",
                    "code": "BAD_REQUEST",
                    "status_code": 400,
                }
            }
        },
    },
    401: {
        "description": "Unauthorized - Authentication required",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid or expired token",
                    "code": "AUTHENTICATION_ERROR",
                    "status_code": 401,
                }
            }
        },
    },
    403: {
        "description": "Forbidden - Insufficient permissions",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Access denied",
                    "code": "FORBIDDEN",
                    "status_code": 403,
                }
            }
        },
    },
    404: {
        "description": "Not Found - Resource does not exist",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Resource not found",
                    "code": "NOT_FOUND",
                    "status_code": 404,
                }
            }
        },
    },
    409: {
        "description": "Conflict - Resource already exists",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Resource already exists",
                    "code": "CONFLICT",
                    "status_code": 409,
                }
            }
        },
    },
    422: {
        "description": "Validation Error - Invalid request format",
        "model": ValidationErrorResponse,
    },
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Try again later.",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "status_code": 429,
                }
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Internal server error",
                    "code": "INTERNAL_ERROR",
                    "status_code": 500,
                }
            }
        },
    },
    503: {
        "description": "Service Unavailable - Database or external service down",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Database temporarily unavailable",
                    "code": "SERVICE_UNAVAILABLE",
                    "status_code": 503,
                }
            }
        },
    },
}
