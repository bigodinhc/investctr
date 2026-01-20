"""
Investment fund position schemas.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin, TimestampMixin


class InvestmentFundPositionBase(BaseSchema):
    """Base schema for investment fund positions."""

    fund_name: str = Field(..., max_length=500, description="Fund name")
    cnpj: str | None = Field(None, max_length=20, description="Fund CNPJ")
    quota_quantity: Decimal = Field(..., description="Number of quotas held")
    quota_price: Decimal | None = Field(None, description="Price per quota")
    gross_balance: Decimal = Field(..., description="Gross balance (saldo bruto)")
    ir_provision: Decimal | None = Field(None, description="IR tax provision")
    net_balance: Decimal | None = Field(None, description="Net balance (saldo liquido)")
    performance_pct: Decimal | None = Field(
        None, description="Monthly performance percentage"
    )
    reference_date: date = Field(..., description="Reference date from statement")


class InvestmentFundPositionCreate(InvestmentFundPositionBase):
    """Schema for creating an investment fund position."""

    account_id: UUID = Field(..., description="Account ID")
    document_id: UUID | None = Field(None, description="Source document ID")


class InvestmentFundPositionResponse(
    InvestmentFundPositionBase, IDMixin, TimestampMixin
):
    """Schema for investment fund position response."""

    account_id: UUID
    document_id: UUID | None = None


class InvestmentFundPositionsListResponse(BaseSchema):
    """Response with list of investment fund positions."""

    positions: list[InvestmentFundPositionResponse]
    total: int
