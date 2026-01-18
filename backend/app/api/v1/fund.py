"""
Fund management endpoints.

Provides endpoints for NAV, fund shares, and performance metrics.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AuthenticatedUser, DBSession
from app.core.logging import get_logger
from app.schemas.fund import (
    FundPerformanceResponse,
    FundShareResponse,
    FundSharesListResponse,
    NAVResponse,
)
from app.services.nav_service import NAVService

logger = get_logger(__name__)
router = APIRouter(prefix="/fund", tags=["fund"])


# -------------------------------------------------------------------------
# NAV Endpoints
# -------------------------------------------------------------------------


@router.get("/nav", response_model=NAVResponse)
async def get_current_nav(
    user: AuthenticatedUser,
    db: DBSession,
    target_date: date | None = Query(None, description="Date for NAV calculation (defaults to today)"),
) -> NAVResponse:
    """
    Get current NAV for the authenticated user.

    Returns the Net Asset Value calculated as:
    NAV = Total Market Value of Positions + Cash Balance
    """
    nav_service = NAVService(db)
    result = await nav_service.calculate_nav(user.id, target_date)

    return NAVResponse(
        user_id=result.user_id,
        date=result.date,
        nav=result.nav,
        total_market_value=result.total_market_value,
        total_cash=result.total_cash,
        positions_count=result.positions_count,
        positions_with_prices=result.positions_with_prices,
    )


# -------------------------------------------------------------------------
# Fund Shares Endpoints
# -------------------------------------------------------------------------


@router.get("/shares", response_model=FundSharesListResponse)
async def get_shares_history(
    user: AuthenticatedUser,
    db: DBSession,
    start_date: date | None = Query(None, description="Start date filter"),
    end_date: date | None = Query(None, description="End date filter"),
    limit: int = Query(30, ge=1, le=365, description="Maximum number of records"),
) -> FundSharesListResponse:
    """
    Get fund shares history for the authenticated user.

    Returns list of FundShare records with NAV, share value, and returns.
    """
    nav_service = NAVService(db)
    shares = await nav_service.get_fund_shares_history(
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    items = [
        FundShareResponse(
            id=share.id,
            user_id=share.user_id,
            date=share.date,
            nav=share.nav,
            shares_outstanding=share.shares_outstanding,
            share_value=share.share_value,
            daily_return=share.daily_return,
            cumulative_return=share.cumulative_return,
            created_at=share.created_at,
        )
        for share in shares
    ]

    return FundSharesListResponse(items=items, total=len(items))


@router.get("/shares/latest", response_model=FundShareResponse)
async def get_latest_share(
    user: AuthenticatedUser,
    db: DBSession,
) -> FundShareResponse:
    """
    Get the most recent fund share record.

    Returns the latest NAV, share value, and outstanding shares.
    """
    nav_service = NAVService(db)
    share = await nav_service.get_latest_fund_share(user.id)

    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No fund share records found",
        )

    return FundShareResponse(
        id=share.id,
        user_id=share.user_id,
        date=share.date,
        nav=share.nav,
        shares_outstanding=share.shares_outstanding,
        share_value=share.share_value,
        daily_return=share.daily_return,
        cumulative_return=share.cumulative_return,
        created_at=share.created_at,
    )


# -------------------------------------------------------------------------
# Performance Endpoints
# -------------------------------------------------------------------------


@router.get("/performance", response_model=FundPerformanceResponse)
async def get_performance(
    user: AuthenticatedUser,
    db: DBSession,
) -> FundPerformanceResponse:
    """
    Get comprehensive fund performance metrics.

    Returns:
    - Current NAV and share value
    - Daily, MTD, YTD, and 1Y returns
    - Maximum drawdown
    - Annualized volatility
    """
    nav_service = NAVService(db)
    performance = await nav_service.get_fund_performance(user.id)

    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No performance data available",
        )

    return FundPerformanceResponse(
        current_nav=performance.current_nav,
        current_share_value=performance.current_share_value,
        shares_outstanding=performance.shares_outstanding,
        total_return=performance.total_return,
        daily_return=performance.daily_return,
        mtd_return=performance.mtd_return,
        ytd_return=performance.ytd_return,
        one_year_return=performance.one_year_return,
        max_drawdown=performance.max_drawdown,
        volatility=performance.volatility,
    )


# -------------------------------------------------------------------------
# Manual Calculation Endpoints (for testing/debugging)
# -------------------------------------------------------------------------


@router.post("/shares/calculate", response_model=FundShareResponse)
async def calculate_daily_share(
    user: AuthenticatedUser,
    db: DBSession,
    target_date: date | None = Query(None, description="Date for calculation (defaults to today)"),
) -> FundShareResponse:
    """
    Manually trigger daily fund share calculation.

    Creates or updates the FundShare record for the specified date.
    Normally this runs automatically via Celery at 19:00 BRT.
    """
    nav_service = NAVService(db)
    share = await nav_service.create_daily_fund_share(user.id, target_date)

    if not share:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not calculate fund share (zero NAV or no positions)",
        )

    await db.commit()

    return FundShareResponse(
        id=share.id,
        user_id=share.user_id,
        date=share.date,
        nav=share.nav,
        shares_outstanding=share.shares_outstanding,
        share_value=share.share_value,
        daily_return=share.daily_return,
        cumulative_return=share.cumulative_return,
        created_at=share.created_at,
    )
