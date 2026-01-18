"""
CashFlow schemas for request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin
from app.schemas.enums import CashFlowType, Currency


class CashFlowBase(BaseSchema):
    """Base cash flow schema with common fields."""

    account_id: UUID = Field(..., description="Account ID for the cash flow")
    type: CashFlowType = Field(..., description="Type of cash flow (deposit/withdrawal)")
    amount: Decimal = Field(..., gt=0, description="Amount of the cash flow (always positive)")
    currency: Currency = Field(default=Currency.BRL, description="Currency of the cash flow")
    exchange_rate: Decimal = Field(default=Decimal("1"), description="Exchange rate to BRL")
    executed_at: datetime = Field(..., description="Date and time the cash flow was executed")
    notes: str | None = Field(None, max_length=500, description="Optional notes")


class CashFlowCreate(CashFlowBase):
    """Schema for creating a new cash flow."""

    shares_affected: Decimal | None = Field(None, description="Shares affected (for fund operations)")


class CashFlowUpdate(BaseSchema):
    """Schema for updating a cash flow."""

    type: CashFlowType | None = Field(None, description="Type of cash flow")
    amount: Decimal | None = Field(None, gt=0, description="Amount of the cash flow")
    currency: Currency | None = Field(None, description="Currency")
    exchange_rate: Decimal | None = Field(None, description="Exchange rate to BRL")
    executed_at: datetime | None = Field(None, description="Execution date")
    shares_affected: Decimal | None = Field(None, description="Shares affected")
    notes: str | None = Field(None, max_length=500, description="Notes")


class CashFlowResponse(CashFlowBase, IDMixin):
    """Cash flow response schema."""

    shares_affected: Decimal | None = None
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "223e4567-e89b-12d3-a456-426614174000",
                "type": "deposit",
                "amount": "10000.00",
                "currency": "BRL",
                "exchange_rate": "1.000000",
                "executed_at": "2026-01-15T10:30:00Z",
                "shares_affected": None,
                "notes": "Monthly investment",
                "created_at": "2026-01-15T10:30:00Z",
            }
        }


class CashFlowsListResponse(BaseSchema):
    """Response for listing cash flows."""

    items: list[CashFlowResponse]
    total: int
