"""
Fixed income position schemas.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin, TimestampMixin
from app.schemas.enums import FixedIncomeType, IndexerType


class FixedIncomePositionBase(BaseSchema):
    """Base schema for fixed income positions."""

    asset_name: str = Field(..., max_length=255, description="Asset name/identifier")
    asset_type: FixedIncomeType = Field(..., description="Type of fixed income asset")
    issuer: str | None = Field(None, max_length=255, description="Issuing institution")
    quantity: Decimal = Field(..., description="Quantity/units")
    unit_price: Decimal | None = Field(None, description="Unit price")
    total_value: Decimal = Field(..., description="Total value")
    indexer: IndexerType | None = Field(
        None, description="Index type (CDI, SELIC, etc)"
    )
    rate_percent: Decimal | None = Field(None, description="Rate percentage")
    acquisition_date: date | None = Field(None, description="Acquisition date")
    maturity_date: date | None = Field(None, description="Maturity date")
    reference_date: date = Field(..., description="Reference date from statement")


class FixedIncomePositionCreate(FixedIncomePositionBase):
    """Schema for creating a fixed income position."""

    account_id: UUID = Field(..., description="Account ID")
    document_id: UUID | None = Field(None, description="Source document ID")


class FixedIncomePositionResponse(FixedIncomePositionBase, IDMixin, TimestampMixin):
    """Schema for fixed income position response."""

    account_id: UUID
    document_id: UUID | None = None


class FixedIncomePositionsListResponse(BaseSchema):
    """Response with list of fixed income positions."""

    positions: list[FixedIncomePositionResponse]
    total: int
