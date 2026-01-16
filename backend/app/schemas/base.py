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
