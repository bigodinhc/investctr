"""
Fund schemas for request/response validation.

Includes schemas for NAV, fund shares, and performance metrics.
"""

import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, IDMixin


# -------------------------------------------------------------------------
# NAV Schemas
# -------------------------------------------------------------------------


class NAVResponse(BaseSchema):
    """Response for current NAV calculation."""

    user_id: UUID = Field(..., description="User ID")
    date: dt.date = Field(..., description="Date of NAV calculation")
    nav: Decimal = Field(..., description="Net Asset Value")
    total_market_value: Decimal = Field(..., description="Total market value of positions")
    total_cash: Decimal = Field(..., description="Total cash balance")
    positions_count: int = Field(..., description="Number of positions")
    positions_with_prices: int = Field(..., description="Positions with available prices")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "date": "2026-01-18",
                "nav": "150000.00",
                "total_market_value": "145000.00",
                "total_cash": "5000.00",
                "positions_count": 15,
                "positions_with_prices": 15,
            }
        }


# -------------------------------------------------------------------------
# Fund Share Schemas
# -------------------------------------------------------------------------


class FundShareResponse(BaseSchema, IDMixin):
    """Response for a single fund share record."""

    user_id: UUID = Field(..., description="User ID")
    date: dt.date = Field(..., description="Date of the record")
    nav: Decimal = Field(..., description="Net Asset Value")
    shares_outstanding: Decimal = Field(..., description="Total shares outstanding")
    share_value: Decimal = Field(..., description="Value per share")
    daily_return: Decimal | None = Field(None, description="Daily return as decimal (0.01 = 1%)")
    cumulative_return: Decimal | None = Field(None, description="Cumulative return since inception")
    created_at: dt.datetime = Field(..., description="Record creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "223e4567-e89b-12d3-a456-426614174000",
                "date": "2026-01-18",
                "nav": "150000.00",
                "shares_outstanding": "1234.56789012",
                "share_value": "121.50123456",
                "daily_return": "0.002345",
                "cumulative_return": "0.215012",
                "created_at": "2026-01-18T19:00:00Z",
            }
        }


class FundSharesListResponse(BaseSchema):
    """Response for listing fund shares."""

    items: list[FundShareResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of records")


# -------------------------------------------------------------------------
# Performance Schemas
# -------------------------------------------------------------------------


class FundPerformanceResponse(BaseSchema):
    """Response for fund performance metrics."""

    current_nav: Decimal = Field(..., description="Current NAV")
    current_share_value: Decimal = Field(..., description="Current value per share")
    shares_outstanding: Decimal = Field(..., description="Total shares outstanding")
    total_return: Decimal | None = Field(None, description="Cumulative return since inception")
    daily_return: Decimal | None = Field(None, description="Latest daily return")
    mtd_return: Decimal | None = Field(None, description="Month-to-date return")
    ytd_return: Decimal | None = Field(None, description="Year-to-date return")
    one_year_return: Decimal | None = Field(None, description="One year return")
    max_drawdown: Decimal | None = Field(None, description="Maximum drawdown from peak")
    volatility: Decimal | None = Field(None, description="Annualized volatility")

    class Config:
        json_schema_extra = {
            "example": {
                "current_nav": "150000.00",
                "current_share_value": "121.50123456",
                "shares_outstanding": "1234.56789012",
                "total_return": "0.215012",
                "daily_return": "0.002345",
                "mtd_return": "0.023456",
                "ytd_return": "0.089012",
                "one_year_return": "0.156789",
                "max_drawdown": "0.082345",
                "volatility": "0.145678",
            }
        }


# -------------------------------------------------------------------------
# Share Operation Schemas
# -------------------------------------------------------------------------


class SharesOperationResponse(BaseSchema):
    """Response for share issuance or redemption."""

    cash_flow_id: UUID = Field(..., description="Related cash flow ID")
    amount: Decimal = Field(..., description="Amount in BRL")
    share_value: Decimal = Field(..., description="Share value used (D-1)")
    shares_affected: Decimal = Field(..., description="Shares issued (+) or redeemed (-)")
    new_shares_outstanding: Decimal = Field(..., description="New total shares outstanding")

    class Config:
        json_schema_extra = {
            "example": {
                "cash_flow_id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": "10000.00",
                "share_value": "121.50123456",
                "shares_affected": "82.30123456",
                "new_shares_outstanding": "1316.86912468",
            }
        }


# -------------------------------------------------------------------------
# Portfolio History Schemas
# -------------------------------------------------------------------------


class PortfolioHistoryItem(BaseSchema):
    """Single item in portfolio history."""

    date: dt.date = Field(..., description="Date of the snapshot")
    nav: Decimal = Field(..., description="Net Asset Value")
    total_cost: Decimal = Field(..., description="Total cost basis")
    realized_pnl: Decimal = Field(..., description="Realized P&L")
    unrealized_pnl: Decimal = Field(..., description="Unrealized P&L")

    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-01-18",
                "nav": "150000.00",
                "total_cost": "120000.00",
                "realized_pnl": "5000.00",
                "unrealized_pnl": "30000.00",
            }
        }


class PortfolioHistoryResponse(BaseSchema):
    """Response for portfolio history."""

    items: list[PortfolioHistoryItem] = Field(default_factory=list)
    total: int = Field(..., description="Total number of records")
    period_return: Decimal | None = Field(None, description="Return for the selected period")
    start_nav: Decimal | None = Field(None, description="NAV at period start")
    end_nav: Decimal | None = Field(None, description="NAV at period end")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "date": "2026-01-18",
                        "nav": "150000.00",
                        "total_cost": "120000.00",
                        "realized_pnl": "5000.00",
                        "unrealized_pnl": "30000.00",
                    }
                ],
                "total": 252,
                "period_return": "0.089012",
                "start_nav": "138000.00",
                "end_nav": "150000.00",
            }
        }
