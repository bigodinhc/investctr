"""
Position management endpoints.
"""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.core.logging import get_logger
from app.models import Account, Asset, Position
from app.schemas.enums import AssetType
from app.schemas.position import (
    ConsolidatedPosition,
    ConsolidatedPositionsResponse,
    PortfolioSummary,
    PositionResponse,
    PositionsListResponse,
    PositionSummary,
    PositionsWithAssetListResponse,
    PositionsWithMarketDataResponse,
    PositionWithAsset,
    PositionWithMarketData,
)
from app.services.pnl_service import PnLService
from app.services.position_service import PositionService
from app.services.quote_service import QuoteService

logger = get_logger(__name__)
router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=PositionsWithMarketDataResponse)
async def list_positions(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
    account_id: UUID | None = Query(None, description="Filter by account"),
    asset_type: AssetType | None = Query(None, description="Filter by asset type"),
    min_value: Decimal | None = Query(None, description="Filter by minimum market value"),
) -> PositionsWithMarketDataResponse:
    """
    List all positions for the authenticated user.

    Returns positions with asset info and market data (if available).
    Supports filtering by account and asset type.
    Includes current_price, unrealized_pnl, and unrealized_pnl_pct from quotes.
    """
    # Base query with joins
    query = (
        select(Position)
        .join(Position.account)
        .join(Position.asset)
        .options(selectinload(Position.asset))
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)  # Only non-zero positions
        .offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(Position.total_cost.desc())
    )

    if account_id:
        query = query.where(Position.account_id == account_id)
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)

    result = await db.execute(query)
    positions = list(result.scalars().all())

    # Get total count
    count_query = (
        select(func.count(Position.id))
        .join(Position.account)
        .join(Position.asset)
        .where(Account.user_id == user.id)
        .where(Position.quantity > 0)
    )
    if account_id:
        count_query = count_query.where(Position.account_id == account_id)
    if asset_type:
        count_query = count_query.where(Asset.asset_type == asset_type)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get current prices for all positions
    asset_ids = [pos.asset_id for pos in positions]
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_latest_prices(asset_ids) if asset_ids else {}

    # Calculate unrealized P&L using PnLService
    pnl_service = PnLService(db)
    unrealized_summary = await pnl_service.calculate_unrealized_pnl(positions, current_prices)

    # Build a lookup map for unrealized P&L by position_id
    unrealized_by_position = {
        entry.position_id: entry for entry in unrealized_summary.entries
    }

    # Build response items
    items = []
    for pos in positions:
        pnl_entry = unrealized_by_position.get(pos.id)

        item = PositionWithMarketData(
            id=pos.id,
            account_id=pos.account_id,
            asset_id=pos.asset_id,
            quantity=pos.quantity,
            avg_price=pos.avg_price,
            total_cost=pos.total_cost,
            position_type=pos.position_type,
            opened_at=pos.opened_at,
            updated_at=pos.updated_at,
            ticker=pos.asset.ticker,
            asset_name=pos.asset.name,
            asset_type=pos.asset.asset_type,
            current_price=pnl_entry.current_price if pnl_entry else None,
            market_value=pnl_entry.market_value if pnl_entry else None,
            unrealized_pnl=pnl_entry.unrealized_pnl if pnl_entry else None,
            unrealized_pnl_pct=pnl_entry.unrealized_pnl_pct if pnl_entry else None,
            price_updated_at=None,  # TODO: Get from quote timestamp
        )
        items.append(item)

    # Filter by min_value after market data enrichment
    if min_value is not None:
        items = [item for item in items if (item.market_value or item.total_cost) >= min_value]

    return PositionsWithMarketDataResponse(
        items=items,
        total=total,
        total_market_value=unrealized_summary.total_market_value if unrealized_summary.total_market_value > 0 else unrealized_summary.total_cost,
        total_cost=unrealized_summary.total_cost,
        total_unrealized_pnl=unrealized_summary.total_unrealized_pnl,
        total_unrealized_pnl_pct=unrealized_summary.total_unrealized_pnl_pct,
    )


@router.get("/consolidated", response_model=ConsolidatedPositionsResponse)
async def get_consolidated_positions(
    user: AuthenticatedUser,
    db: DBSession,
    asset_type: AssetType | None = Query(None, description="Filter by asset type"),
) -> ConsolidatedPositionsResponse:
    """
    Get positions consolidated across all accounts.

    For users with multiple accounts, this aggregates positions for the same
    asset, showing total quantity and weighted average price.
    """
    position_service = PositionService(db)
    consolidated_data = await position_service.get_consolidated_positions(user.id)

    # Apply asset type filter
    if asset_type:
        consolidated_data = [p for p in consolidated_data if p["asset_type"] == asset_type]

    # Calculate totals
    total_cost = Decimal("0")
    total_market_value = Decimal("0")

    items = []
    for data in consolidated_data:
        item = ConsolidatedPosition(
            asset_id=data["asset_id"],
            ticker=data["ticker"],
            asset_name=data["asset_name"],
            asset_type=data["asset_type"],
            total_quantity=data["total_quantity"],
            weighted_avg_price=data["weighted_avg_price"],
            total_cost=data["total_cost"],
            current_price=data["current_price"],
            market_value=data["market_value"],
            unrealized_pnl=data["unrealized_pnl"],
            unrealized_pnl_pct=data["unrealized_pnl_pct"],
            accounts_count=data["accounts_count"],
        )
        items.append(item)
        total_cost += data["total_cost"]

        if data["market_value"] is not None:
            total_market_value += data["market_value"]

    total_unrealized_pnl = total_market_value - total_cost if total_market_value > 0 else Decimal("0")
    total_unrealized_pnl_pct = (
        (total_unrealized_pnl / total_cost * 100) if total_cost > 0 and total_market_value > 0 else None
    )

    return ConsolidatedPositionsResponse(
        items=items,
        total=len(items),
        total_market_value=total_market_value if total_market_value > 0 else total_cost,
        total_cost=total_cost,
        total_unrealized_pnl=total_unrealized_pnl,
        total_unrealized_pnl_pct=total_unrealized_pnl_pct,
    )


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID | None = Query(None, description="Filter by account"),
) -> PortfolioSummary:
    """
    Get portfolio summary with breakdown by asset type.

    Returns high-level metrics and allocation percentages.
    """
    # Base query
    base_filters = [Account.user_id == user.id, Position.quantity > 0]
    if account_id:
        base_filters.append(Position.account_id == account_id)

    # Get total counts and values
    totals_query = (
        select(
            func.count(Position.id).label("positions_count"),
            func.sum(Position.total_cost).label("total_cost"),
        )
        .join(Position.account)
        .where(*base_filters)
    )
    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    total_positions = totals.positions_count or 0
    total_cost = totals.total_cost or Decimal("0")

    # Get breakdown by asset type
    by_type_query = (
        select(
            Asset.asset_type,
            func.count(Position.id).label("positions_count"),
            func.sum(Position.total_cost).label("total_cost"),
        )
        .join(Position.account)
        .join(Position.asset)
        .where(*base_filters)
        .group_by(Asset.asset_type)
    )
    by_type_result = await db.execute(by_type_query)
    by_type_rows = by_type_result.fetchall()

    by_asset_type = []
    for row in by_type_rows:
        type_cost = row.total_cost or Decimal("0")
        allocation_pct = (type_cost / total_cost * 100) if total_cost > 0 else None

        summary = PositionSummary(
            asset_type=row.asset_type,
            positions_count=row.positions_count or 0,
            total_cost=type_cost,
            market_value=None,  # TODO: Get from quotes
            unrealized_pnl=None,
            allocation_pct=allocation_pct,
        )
        by_asset_type.append(summary)

    # Sort by allocation descending
    by_asset_type.sort(key=lambda x: x.total_cost, reverse=True)

    return PortfolioSummary(
        total_positions=total_positions,
        total_cost=total_cost,
        total_market_value=None,  # TODO: Calculate from quotes
        total_unrealized_pnl=None,
        total_unrealized_pnl_pct=None,
        by_asset_type=by_asset_type,
        last_updated=None,  # TODO: Get latest quote timestamp
    )


@router.get("/{position_id}", response_model=PositionWithMarketData)
async def get_position(
    user: AuthenticatedUser,
    db: DBSession,
    position_id: UUID,
) -> PositionWithMarketData:
    """Get a specific position by ID with current market data."""
    query = (
        select(Position)
        .join(Position.account)
        .options(selectinload(Position.asset))
        .where(Position.id == position_id)
        .where(Account.user_id == user.id)
    )
    result = await db.execute(query)
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found",
        )

    # Get current price
    quote_service = QuoteService(db)
    current_price = await quote_service.get_latest_price(position.asset_id)

    # Calculate unrealized P&L
    market_value = None
    unrealized_pnl = None
    unrealized_pnl_pct = None

    if current_price is not None and position.quantity > 0:
        market_value = position.quantity * current_price
        unrealized_pnl = market_value - position.total_cost
        unrealized_pnl_pct = (
            (unrealized_pnl / position.total_cost * 100)
            if position.total_cost > 0
            else Decimal("0")
        )

    return PositionWithMarketData(
        id=position.id,
        account_id=position.account_id,
        asset_id=position.asset_id,
        quantity=position.quantity,
        avg_price=position.avg_price,
        total_cost=position.total_cost,
        position_type=position.position_type,
        opened_at=position.opened_at,
        updated_at=position.updated_at,
        ticker=position.asset.ticker,
        asset_name=position.asset.name,
        asset_type=position.asset.asset_type,
        current_price=current_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        price_updated_at=None,  # TODO: Get from quote timestamp
    )


@router.post("/{account_id}/recalculate", status_code=status.HTTP_200_OK)
async def recalculate_account_positions(
    user: AuthenticatedUser,
    db: DBSession,
    account_id: UUID,
) -> dict:
    """
    Recalculate all positions for an account.

    Use this to fix any position inconsistencies by recalculating
    from the complete transaction history.
    """
    # Validate account belongs to user
    account_query = (
        select(Account)
        .where(Account.id == account_id)
        .where(Account.user_id == user.id)
    )
    account_result = await db.execute(account_query)
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    position_service = PositionService(db)
    positions = await position_service.recalculate_account_positions(account_id)

    logger.info(
        "positions_recalculated",
        account_id=str(account_id),
        positions_count=len(positions),
    )

    return {
        "message": f"Recalculated {len(positions)} positions",
        "positions_updated": len(positions),
    }
