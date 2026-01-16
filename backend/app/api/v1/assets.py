"""
Asset management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthenticatedUser, DBSession, Pagination
from app.models import Asset
from app.schemas.asset import (
    AssetCreate,
    AssetResponse,
    AssetsListResponse,
)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetsListResponse)
async def list_assets(
    user: AuthenticatedUser,
    db: DBSession,
    pagination: Pagination,
) -> AssetsListResponse:
    """List all active assets."""
    query = (
        select(Asset)
        .where(Asset.is_active == True)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .order_by(Asset.ticker)
    )
    result = await db.execute(query)
    assets = result.scalars().all()

    # Get total count
    count_query = select(func.count(Asset.id)).where(Asset.is_active == True)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return AssetsListResponse(
        items=[AssetResponse.model_validate(asset) for asset in assets],
        total=total,
    )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    user: AuthenticatedUser,
    db: DBSession,
    asset_in: AssetCreate,
) -> AssetResponse:
    """Create a new asset."""
    asset = Asset(
        ticker=asset_in.ticker.upper(),
        name=asset_in.name,
        asset_type=asset_in.asset_type,
        currency=asset_in.currency.value,
        exchange=asset_in.exchange,
        sector=asset_in.sector,
        lseg_ric=asset_in.lseg_ric,
    )

    try:
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with ticker '{asset_in.ticker}' already exists",
        ) from e

    return AssetResponse.model_validate(asset)


@router.get("/search", response_model=AssetsListResponse)
async def search_assets(
    user: AuthenticatedUser,
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search query (ticker or name)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
) -> AssetsListResponse:
    """Search assets by ticker or name."""
    search_term = f"%{q.upper()}%"
    query = (
        select(Asset)
        .where(Asset.is_active == True)
        .where(
            or_(
                Asset.ticker.ilike(search_term),
                Asset.name.ilike(search_term),
            )
        )
        .limit(limit)
        .order_by(Asset.ticker)
    )
    result = await db.execute(query)
    assets = result.scalars().all()

    return AssetsListResponse(
        items=[AssetResponse.model_validate(asset) for asset in assets],
        total=len(assets),
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    user: AuthenticatedUser,
    db: DBSession,
    asset_id: UUID,
) -> AssetResponse:
    """Get a specific asset by ID."""
    query = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return AssetResponse.model_validate(asset)


@router.get("/ticker/{ticker}", response_model=AssetResponse)
async def get_asset_by_ticker(
    user: AuthenticatedUser,
    db: DBSession,
    ticker: str,
) -> AssetResponse:
    """Get a specific asset by ticker symbol."""
    query = select(Asset).where(Asset.ticker == ticker.upper())
    result = await db.execute(query)
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ticker '{ticker}' not found",
        )

    return AssetResponse.model_validate(asset)
