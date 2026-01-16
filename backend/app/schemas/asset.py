"""
Asset schemas for request/response validation.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin, TimestampMixin
from app.schemas.enums import AssetType, Currency


class AssetBase(BaseSchema):
    """Base asset schema with common fields."""

    ticker: str = Field(
        ..., min_length=1, max_length=20, description="Asset ticker symbol"
    )
    name: str = Field(..., min_length=1, max_length=200, description="Asset full name")
    asset_type: AssetType = Field(..., description="Type of asset")
    currency: Currency = Field(default=Currency.BRL, description="Asset currency")
    exchange: str | None = Field(
        None, max_length=20, description="Exchange where asset is traded"
    )
    sector: str | None = Field(None, max_length=100, description="Sector classification")


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    lseg_ric: str | None = Field(
        None, max_length=30, description="LSEG RIC code for market data"
    )


class AssetInDB(AssetBase, IDMixin, TimestampMixin):
    """Asset as stored in database."""

    lseg_ric: str | None = None
    is_active: bool = True


class AssetResponse(AssetBase, IDMixin):
    """Asset response schema."""

    is_active: bool
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "ticker": "VALE3",
                "name": "Vale S.A.",
                "asset_type": "stock",
                "currency": "BRL",
                "exchange": "B3",
                "sector": "Mining",
                "is_active": True,
                "created_at": "2026-01-15T10:30:00Z",
            }
        }


class AssetsListResponse(BaseSchema):
    """Response for listing assets."""

    items: list[AssetResponse]
    total: int


class AssetWithPrice(AssetResponse):
    """Asset with current price information."""

    current_price: float | None = None
    price_date: datetime | None = None
    price_change_pct: float | None = None
