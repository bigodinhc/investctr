"""
Portfolio management endpoints.

Provides aggregated portfolio views and summaries with realized and unrealized P&L.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, DBSession
from app.core.logging import get_logger
from app.models import Account, Asset, Position
from app.schemas.enums import AssetType
from app.services.pnl_service import PnLService
from app.services.position_service import PositionService
from app.services.quote_service import QuoteService

logger = get_logger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# -------------------------------------------------------------------------
# Response Schemas
# -------------------------------------------------------------------------


class AssetTypeSummary(BaseModel):
    """Summary for a specific asset type."""

    asset_type: AssetType
    positions_count: int
    total_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    allocation_pct: Decimal | None = Field(None, description="% of total portfolio")


class AccountSummary(BaseModel):
    """Summary for a specific account."""

    account_id: UUID
    account_name: str
    broker: str | None = None
    positions_count: int
    total_cost: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    unrealized_pnl_pct: Decimal | None = None
    allocation_pct: Decimal | None = Field(None, description="% of total portfolio")


class PortfolioSummaryResponse(BaseModel):
    """Comprehensive portfolio summary response."""

    # Totals
    total_positions: int = Field(..., description="Total number of positions")
    total_value: Decimal = Field(..., description="Total market value (or cost if no prices)")
    total_cost: Decimal = Field(..., description="Total cost basis")
    total_unrealized_pnl: Decimal = Field(..., description="Total unrealized P&L")
    total_unrealized_pnl_pct: Decimal | None = Field(None, description="Total unrealized P&L %")
    total_realized_pnl: Decimal = Field(..., description="Total realized P&L (all time)")

    # Breakdowns
    by_asset_type: list[AssetTypeSummary] = Field(
        default_factory=list,
        description="Summary grouped by asset type",
    )
    by_account: list[AccountSummary] = Field(
        default_factory=list,
        description="Summary grouped by account (only if not filtered by account)",
    )

    # Metadata
    accounts_count: int = Field(..., description="Number of accounts included")
    last_price_update: datetime | None = Field(None, description="Latest quote timestamp")


# -------------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------------


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID | None = Query(None, description="Filter by specific account"),
) -> PortfolioSummaryResponse:
    """
    Get comprehensive portfolio summary.

    Returns aggregated portfolio metrics including:
    - Total value, cost, and unrealized P&L
    - Total realized P&L (from all sales)
    - Breakdown by asset type
    - Breakdown by account (if not filtered)

    If account_id is provided, returns summary for that account only.
    Otherwise, returns consolidated summary across all user accounts.
    """
    # Build base query for positions
    base_query = (
        select(Position)
        .join(Position.account)
        .join(Position.asset)
        .options(selectinload(Position.asset), selectinload(Position.account))
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)
    )

    if account_id:
        base_query = base_query.where(Position.account_id == account_id)

    result = await db.execute(base_query)
    positions = list(result.scalars().all())

    if not positions:
        return PortfolioSummaryResponse(
            total_positions=0,
            total_value=Decimal("0"),
            total_cost=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_unrealized_pnl_pct=None,
            total_realized_pnl=Decimal("0"),
            by_asset_type=[],
            by_account=[],
            accounts_count=0,
            last_price_update=None,
        )

    # Get current prices for all assets
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids)

    # Calculate unrealized P&L
    pnl_service = PnLService(db)
    unrealized_summary = await pnl_service.calculate_unrealized_pnl(positions, current_prices)

    # Calculate realized P&L
    realized_summary = await pnl_service.calculate_realized_pnl(
        account_id=account_id,
        user_id=user.id if not account_id else None,
    )

    # Build lookup maps
    unrealized_by_position = {
        entry.position_id: entry for entry in unrealized_summary.entries
    }

    # Calculate totals
    total_cost = unrealized_summary.total_cost
    total_market_value = unrealized_summary.total_market_value
    total_unrealized_pnl = unrealized_summary.total_unrealized_pnl
    total_unrealized_pnl_pct = unrealized_summary.total_unrealized_pnl_pct

    # Use market value if available, otherwise use cost
    total_value = total_market_value if total_market_value > 0 else total_cost

    # Group by asset type
    by_asset_type_data: dict[AssetType, dict] = {}
    for pos in positions:
        asset_type = pos.asset.asset_type
        pnl_entry = unrealized_by_position.get(pos.id)

        if asset_type not in by_asset_type_data:
            by_asset_type_data[asset_type] = {
                "positions_count": 0,
                "total_cost": Decimal("0"),
                "market_value": Decimal("0"),
            }

        data = by_asset_type_data[asset_type]
        data["positions_count"] += 1
        data["total_cost"] += pos.total_cost

        if pnl_entry and pnl_entry.market_value is not None:
            data["market_value"] += pnl_entry.market_value

    # Build by_asset_type response
    by_asset_type = []
    for asset_type, data in by_asset_type_data.items():
        market_value = data["market_value"] if data["market_value"] > 0 else None
        unrealized_pnl = (
            data["market_value"] - data["total_cost"]
            if data["market_value"] > 0
            else None
        )
        unrealized_pnl_pct = (
            (unrealized_pnl / data["total_cost"] * 100)
            if unrealized_pnl is not None and data["total_cost"] > 0
            else None
        )
        allocation_pct = (
            (data["total_cost"] / total_cost * 100)
            if total_cost > 0
            else None
        )

        by_asset_type.append(
            AssetTypeSummary(
                asset_type=asset_type,
                positions_count=data["positions_count"],
                total_cost=data["total_cost"],
                market_value=market_value,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                allocation_pct=allocation_pct,
            )
        )

    # Sort by allocation descending
    by_asset_type.sort(key=lambda x: x.total_cost, reverse=True)

    # Group by account (only if not filtered by account_id)
    by_account = []
    if not account_id:
        by_account_data: dict[UUID, dict] = {}
        for pos in positions:
            acc_id = pos.account_id
            pnl_entry = unrealized_by_position.get(pos.id)

            if acc_id not in by_account_data:
                by_account_data[acc_id] = {
                    "account": pos.account,
                    "positions_count": 0,
                    "total_cost": Decimal("0"),
                    "market_value": Decimal("0"),
                }

            data = by_account_data[acc_id]
            data["positions_count"] += 1
            data["total_cost"] += pos.total_cost

            if pnl_entry and pnl_entry.market_value is not None:
                data["market_value"] += pnl_entry.market_value

        for acc_id, data in by_account_data.items():
            market_value = data["market_value"] if data["market_value"] > 0 else None
            unrealized_pnl = (
                data["market_value"] - data["total_cost"]
                if data["market_value"] > 0
                else None
            )
            unrealized_pnl_pct = (
                (unrealized_pnl / data["total_cost"] * 100)
                if unrealized_pnl is not None and data["total_cost"] > 0
                else None
            )
            allocation_pct = (
                (data["total_cost"] / total_cost * 100)
                if total_cost > 0
                else None
            )

            by_account.append(
                AccountSummary(
                    account_id=acc_id,
                    account_name=data["account"].name,
                    broker=data["account"].broker,
                    positions_count=data["positions_count"],
                    total_cost=data["total_cost"],
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    allocation_pct=allocation_pct,
                )
            )

        # Sort by allocation descending
        by_account.sort(key=lambda x: x.total_cost, reverse=True)

    # Count unique accounts
    unique_accounts = set(pos.account_id for pos in positions)

    return PortfolioSummaryResponse(
        total_positions=len(positions),
        total_value=total_value,
        total_cost=total_cost,
        total_unrealized_pnl=total_unrealized_pnl,
        total_unrealized_pnl_pct=total_unrealized_pnl_pct,
        total_realized_pnl=realized_summary.total_realized_pnl,
        by_asset_type=by_asset_type,
        by_account=by_account,
        accounts_count=len(unique_accounts),
        last_price_update=None,  # TODO: Get from latest quote timestamp
    )
