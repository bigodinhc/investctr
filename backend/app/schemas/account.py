"""
Account schemas for request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin, TimestampMixin
from app.schemas.enums import AccountType, Currency


class AccountBase(BaseSchema):
    """Base account schema with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Account name")
    type: AccountType = Field(..., description="Account type (broker)")
    currency: Currency = Field(default=Currency.BRL, description="Account base currency")


class AccountCreate(AccountBase):
    """Schema for creating a new account."""

    pass


class AccountUpdate(BaseSchema):
    """Schema for updating an account."""

    name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None


class AccountInDB(AccountBase, IDMixin, TimestampMixin):
    """Account as stored in database."""

    user_id: UUID
    is_active: bool = True


class AccountResponse(AccountBase, IDMixin):
    """Account response schema."""

    is_active: bool
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "BTG Principal",
                "type": "btg_br",
                "currency": "BRL",
                "is_active": True,
                "created_at": "2026-01-15T10:30:00Z",
            }
        }


class AccountsListResponse(BaseSchema):
    """Response for listing accounts."""

    items: list[AccountResponse]
    total: int
