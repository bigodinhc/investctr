"""
Quote schemas for API responses.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class QuoteResponse(BaseSchema):
    """Response schema for a single quote."""

    id: UUID
    asset_id: UUID
    date: date
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    close: Decimal
    adjusted_close: Decimal | None = None
    volume: int | None = None
    source: str


class QuoteHistoryResponse(BaseSchema):
    """Response schema for quote history."""

    items: list[QuoteResponse]
    total: int
    asset_id: UUID
    ticker: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class LatestPriceResponse(BaseSchema):
    """Response schema for latest price."""

    asset_id: UUID
    price: Decimal
    date: date
    source: str
    cached: bool = Field(
        default=False,
        description="Whether the price was retrieved from cache",
    )


class LatestPricesResponse(BaseSchema):
    """Response schema for multiple latest prices."""

    items: list[LatestPriceResponse]
    total: int
    cached_count: int = Field(
        default=0,
        description="Number of prices retrieved from cache",
    )
