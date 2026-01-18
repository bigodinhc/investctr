"""
Portfolio management endpoints.

Provides aggregated portfolio views and summaries with realized and unrealized P&L.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, DBSession
from app.core.logging import get_logger
from app.models import Account, Asset, Position, PortfolioSnapshot
from app.schemas.enums import AccountType, AssetType

# Mapping from AccountType to broker display name
ACCOUNT_TYPE_BROKER_MAP: dict[AccountType, str] = {
    AccountType.BTG_BR: "BTG Pactual",
    AccountType.XP: "XP Investimentos",
    AccountType.BTG_CAYMAN: "BTG Pactual (Cayman)",
    AccountType.TESOURO_DIRETO: "Tesouro Direto",
}
from app.schemas.fund import PortfolioHistoryItem, PortfolioHistoryResponse
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


class AllocationItem(BaseModel):
    """Single allocation item for charts."""

    name: str = Field(..., description="Category name (asset type or asset)")
    value: Decimal = Field(..., description="Market value or cost basis")
    percentage: Decimal = Field(..., description="Allocation percentage (0-100)")
    color: str | None = Field(None, description="Suggested color for chart")


class AllocationResponse(BaseModel):
    """Portfolio allocation response for charting."""

    by_asset_type: list[AllocationItem] = Field(
        default_factory=list,
        description="Allocation grouped by asset type",
    )
    by_asset: list[AllocationItem] = Field(
        default_factory=list,
        description="Allocation by individual asset (top positions)",
    )
    total_value: Decimal = Field(..., description="Total portfolio value")
    positions_count: int = Field(..., description="Total number of positions")


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
                    broker=ACCOUNT_TYPE_BROKER_MAP.get(data["account"].type),
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


# -------------------------------------------------------------------------
# Allocation Endpoint
# -------------------------------------------------------------------------

# Color palette for asset types (gold-themed)
ASSET_TYPE_COLORS: dict[AssetType, str] = {
    AssetType.STOCK: "#D4AF37",      # Gold
    AssetType.ETF: "#B8860B",        # Dark golden rod
    AssetType.REIT: "#DAA520",       # Goldenrod
    AssetType.BDR: "#FFD700",        # Gold (bright)
    AssetType.FUND: "#F0E68C",       # Khaki
    AssetType.FII: "#C5B358",        # Vegas gold
    AssetType.FIAGRO: "#E6BE8A",     # Pale gold
    AssetType.BOND: "#EEE8AA",       # Pale goldenrod
    AssetType.TREASURY: "#FAFAD2",   # Light goldenrod yellow
    AssetType.CRYPTO: "#CD853F",     # Peru
    AssetType.OPTION: "#D2691E",     # Chocolate
    AssetType.FUTURE: "#8B4513",     # Saddle brown
}


@router.get("/allocation", response_model=AllocationResponse)
async def get_portfolio_allocation(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID | None = Query(None, description="Filter by specific account"),
    top_assets: int = Query(10, ge=1, le=50, description="Number of top assets to return"),
) -> AllocationResponse:
    """
    Get portfolio allocation for charting.

    Returns allocation breakdown by:
    - Asset type (for donut chart)
    - Individual assets (top N by value)

    Uses market value when available, otherwise falls back to cost basis.
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
        return AllocationResponse(
            by_asset_type=[],
            by_asset=[],
            total_value=Decimal("0"),
            positions_count=0,
        )

    # Get current prices for all assets
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids)

    # Calculate values for each position
    position_values: list[tuple[Position, Decimal]] = []
    for pos in positions:
        # Use market value if price available, otherwise use cost
        price_info = current_prices.get(pos.asset_id)
        if price_info and price_info.get("price"):
            value = pos.quantity * price_info["price"]
        else:
            value = pos.total_cost
        position_values.append((pos, value))

    # Calculate total value
    total_value = sum(v for _, v in position_values)

    if total_value <= 0:
        return AllocationResponse(
            by_asset_type=[],
            by_asset=[],
            total_value=Decimal("0"),
            positions_count=len(positions),
        )

    # Group by asset type
    by_type_data: dict[AssetType, Decimal] = {}
    for pos, value in position_values:
        asset_type = pos.asset.asset_type
        by_type_data[asset_type] = by_type_data.get(asset_type, Decimal("0")) + value

    by_asset_type = [
        AllocationItem(
            name=asset_type.value,
            value=value,
            percentage=round(value / total_value * 100, 2),
            color=ASSET_TYPE_COLORS.get(asset_type),
        )
        for asset_type, value in sorted(
            by_type_data.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    # Group by individual asset (top N)
    by_asset_data: dict[str, tuple[str, Decimal]] = {}
    for pos, value in position_values:
        ticker = pos.asset.ticker
        name = pos.asset.name or ticker
        if ticker in by_asset_data:
            existing_name, existing_value = by_asset_data[ticker]
            by_asset_data[ticker] = (existing_name, existing_value + value)
        else:
            by_asset_data[ticker] = (name, value)

    # Sort by value and take top N
    sorted_assets = sorted(
        by_asset_data.items(),
        key=lambda x: x[1][1],
        reverse=True,
    )[:top_assets]

    by_asset = [
        AllocationItem(
            name=f"{ticker} - {name}",
            value=value,
            percentage=round(value / total_value * 100, 2),
            color=None,  # Let frontend assign colors
        )
        for ticker, (name, value) in sorted_assets
    ]

    return AllocationResponse(
        by_asset_type=by_asset_type,
        by_asset=by_asset,
        total_value=total_value,
        positions_count=len(positions),
    )


# -------------------------------------------------------------------------
# History Endpoint
# -------------------------------------------------------------------------


# Period options for history
PeriodType = Literal["1M", "3M", "6M", "1Y", "YTD", "MAX"]


def _get_period_start_date(period: PeriodType) -> date:
    """Calculate the start date for a given period."""
    today = date.today()

    if period == "1M":
        return today - timedelta(days=30)
    elif period == "3M":
        return today - timedelta(days=90)
    elif period == "6M":
        return today - timedelta(days=180)
    elif period == "1Y":
        return today - timedelta(days=365)
    elif period == "YTD":
        return today.replace(month=1, day=1)
    else:  # MAX
        return date(2000, 1, 1)  # Far enough back to get all data


@router.get("/history", response_model=PortfolioHistoryResponse)
async def get_portfolio_history(
    user: AuthenticatedUser,
    db: DBSession,
    period: PeriodType = Query("YTD", description="Period for history (1M, 3M, 6M, 1Y, YTD, MAX)"),
    account_id: UUID | None = Query(None, description="Filter by specific account"),
    limit: int = Query(365, ge=1, le=1000, description="Maximum number of data points"),
) -> PortfolioHistoryResponse:
    """
    Get portfolio history for charting.

    Returns list of PortfolioSnapshot records for the selected period.
    Used for rendering the NAV evolution chart.
    """
    start_date = _get_period_start_date(period)
    today = date.today()

    # Build query for snapshots
    query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user.id)
        .where(PortfolioSnapshot.date >= start_date)
        .where(PortfolioSnapshot.date <= today)
        .order_by(PortfolioSnapshot.date.asc())
        .limit(limit)
    )

    if account_id:
        query = query.where(PortfolioSnapshot.account_id == account_id)
    else:
        # For consolidated view, get records with null account_id (total)
        # or if none exist, get all records
        query = query.where(PortfolioSnapshot.account_id.is_(None))

    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    # If no consolidated snapshots found, try getting consolidated snapshots aggregated by date
    if not snapshots and not account_id:
        # Get consolidated snapshots (account_id IS NULL) grouped by date
        subquery = (
            select(
                PortfolioSnapshot.date,
                func.sum(PortfolioSnapshot.nav).label("nav"),
                func.sum(PortfolioSnapshot.total_cost).label("total_cost"),
                func.sum(PortfolioSnapshot.realized_pnl).label("realized_pnl"),
                func.sum(PortfolioSnapshot.unrealized_pnl).label("unrealized_pnl"),
            )
            .where(PortfolioSnapshot.user_id == user.id)
            .where(PortfolioSnapshot.account_id.is_(None))
            .where(PortfolioSnapshot.date >= start_date)
            .where(PortfolioSnapshot.date <= today)
            .group_by(PortfolioSnapshot.date)
            .order_by(PortfolioSnapshot.date.asc())
            .limit(limit)
        )

        agg_result = await db.execute(subquery)
        rows = agg_result.fetchall()

        items = [
            PortfolioHistoryItem(
                date=row.date,
                nav=row.nav or Decimal("0"),
                total_cost=row.total_cost or Decimal("0"),
                realized_pnl=row.realized_pnl or Decimal("0"),
                unrealized_pnl=row.unrealized_pnl or Decimal("0"),
            )
            for row in rows
        ]
    else:
        items = [
            PortfolioHistoryItem(
                date=snap.date,
                nav=snap.nav,
                total_cost=snap.total_cost,
                realized_pnl=snap.realized_pnl,
                unrealized_pnl=snap.unrealized_pnl,
            )
            for snap in snapshots
        ]

    # Calculate period return
    period_return: Decimal | None = None
    start_nav: Decimal | None = None
    end_nav: Decimal | None = None

    if len(items) >= 2:
        start_nav = items[0].nav
        end_nav = items[-1].nav
        if start_nav > 0:
            period_return = (end_nav - start_nav) / start_nav

    return PortfolioHistoryResponse(
        items=items,
        total=len(items),
        period_return=period_return,
        start_nav=start_nav,
        end_nav=end_nav,
    )
