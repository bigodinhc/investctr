"""
Position schemas for request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, computed_field

from app.schemas.base import BaseSchema, IDMixin
from app.schemas.enums import PositionType, AssetType


class PositionBase(BaseSchema):
    """Base position schema with common fields."""

    quantity: Decimal = Field(..., description="Number of shares/units held")
    avg_price: Decimal = Field(..., description="Average purchase price")
    total_cost: Decimal = Field(..., description="Total cost basis")
    position_type: PositionType = Field(
        default=PositionType.LONG, description="Type of position"
    )


class PositionResponse(PositionBase, IDMixin):
    """Position response schema."""

    account_id: UUID
    asset_id: UUID
    opened_at: datetime | None = None
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "account_id": "123e4567-e89b-12d3-a456-426614174001",
                "asset_id": "123e4567-e89b-12d3-a456-426614174002",
                "quantity": "500.00000000",
                "avg_price": "58.500000",
                "total_cost": "29250.00",
                "position_type": "long",
                "opened_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-15T14:30:00Z",
            }
        }


class PositionWithAsset(PositionResponse):
    """Position response with asset details."""

    ticker: str = Field(..., description="Asset ticker")
    asset_name: str = Field(..., description="Asset name")
    asset_type: AssetType = Field(..., description="Asset type")


class PositionWithMarketData(PositionWithAsset):
    """Position with current market data and P&L."""

    current_price: Decimal | None = Field(None, description="Current market price")
    market_value: Decimal | None = Field(None, description="Current market value")
    unrealized_pnl: Decimal | None = Field(None, description="Unrealized P&L")
    unrealized_pnl_pct: Decimal | None = Field(
        None, description="Unrealized P&L percentage"
    )
    price_updated_at: datetime | None = Field(
        None, description="Last price update time"
    )

    @computed_field
    @property
    def is_profitable(self) -> bool | None:
        """Returns True if position is profitable."""
        if self.unrealized_pnl is None:
            return None
        return self.unrealized_pnl > 0


class PositionsListResponse(BaseSchema):
    """Response for listing positions."""

    items: list[PositionResponse]
    total: int


class PositionsWithAssetListResponse(BaseSchema):
    """Response for listing positions with asset info."""

    items: list[PositionWithAsset]
    total: int


class PositionsWithMarketDataResponse(BaseSchema):
    """Response for listing positions with market data."""

    items: list[PositionWithMarketData]
    total: int
    total_market_value: Decimal = Field(
        ..., description="Sum of all position market values"
    )
    total_cost: Decimal = Field(..., description="Sum of all position costs")
    total_unrealized_pnl: Decimal = Field(..., description="Sum of all unrealized P&L")
    total_unrealized_pnl_pct: Decimal | None = Field(
        None, description="Total unrealized P&L %"
    )


# ============================================================================
# Consolidated Position schemas
# ============================================================================


class ConsolidatedPosition(BaseSchema):
    """Position consolidated across all accounts for same asset."""

    asset_id: UUID
    ticker: str
    asset_name: str
    asset_type: AssetType
    total_quantity: Decimal = Field(..., description="Total quantity across accounts")
    weighted_avg_price: Decimal = Field(..., description="Weighted average price")
    total_cost: Decimal = Field(..., description="Total cost basis")
    current_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    accounts_count: int = Field(
        ..., description="Number of accounts holding this asset"
    )


class ConsolidatedPositionsResponse(BaseSchema):
    """Response for consolidated positions."""

    items: list[ConsolidatedPosition]
    total: int
    total_market_value: Decimal
    total_cost: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pnl_pct: Decimal | None = None


# ============================================================================
# Position Summary schemas
# ============================================================================


class PositionSummary(BaseSchema):
    """Summary of positions by asset type."""

    asset_type: AssetType
    positions_count: int
    total_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    allocation_pct: Decimal | None = Field(None, description="% of total portfolio")


class PortfolioSummary(BaseSchema):
    """Overall portfolio summary."""

    total_positions: int
    total_cost: Decimal
    total_market_value: Decimal | None = None
    total_unrealized_pnl: Decimal | None = None
    total_unrealized_pnl_pct: Decimal | None = None
    by_asset_type: list[PositionSummary] = Field(default_factory=list)
    last_updated: datetime | None = None
