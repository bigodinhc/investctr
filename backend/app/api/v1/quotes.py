"""
Quote management endpoints.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AuthenticatedUser, DBSession
from app.core.logging import get_logger
from app.models import Asset
from app.schemas.quote import (
    LatestPriceResponse,
    LatestPricesResponse,
    QuoteHistoryResponse,
    QuoteResponse,
)
from app.services.cache_service import (
    get_cached_price,
    get_cached_prices,
    set_cached_price,
    set_cached_prices,
)
from app.services.quote_service import QuoteService

logger = get_logger(__name__)
router = APIRouter(prefix="/quotes", tags=["quotes"])


# -------------------------------------------------------------------------
# Sync Endpoint
# -------------------------------------------------------------------------


class SyncQuotesRequest(BaseModel):
    """Request schema for syncing quotes."""

    tickers: list[str] | None = Field(
        default=None,
        description="List of tickers to sync. If empty, syncs all active assets.",
    )
    start_date: date | None = Field(
        default=None,
        description="Start date for historical data (defaults to today)",
    )
    end_date: date | None = Field(
        default=None,
        description="End date for historical data (defaults to today)",
    )


class SyncQuotesResponse(BaseModel):
    """Response schema for sync operation."""

    quotes_updated: int = Field(..., description="Number of quotes synced")
    tickers_processed: int = Field(..., description="Number of tickers processed")
    message: str


@router.post("/sync", response_model=SyncQuotesResponse)
async def sync_quotes(
    user: AuthenticatedUser,
    db: DBSession,
    request: SyncQuotesRequest | None = None,
) -> SyncQuotesResponse:
    """
    Manually trigger quote synchronization.

    If tickers are provided, only those tickers will be synced.
    If no tickers are provided, all active assets (those with positions) will be synced.

    This endpoint fetches quotes from Yahoo Finance and saves them to the database.
    """
    quote_service = QuoteService(db)

    tickers_to_sync: list[str] = []

    if request and request.tickers:
        # Use provided tickers
        tickers_to_sync = request.tickers
        logger.info(
            "sync_quotes_manual_tickers",
            user_id=str(user.id),
            tickers_count=len(tickers_to_sync),
        )
    else:
        # Get all tickers from user's positions (active assets)
        from app.models import Account, Position

        query = (
            select(Asset.ticker)
            .join(Position, Asset.id == Position.asset_id)
            .join(Account, Position.account_id == Account.id)
            .where(Account.user_id == user.id)
            .where(Position.quantity > 0)
            .distinct()
        )
        result = await db.execute(query)
        tickers_to_sync = [row[0] for row in result.fetchall()]

        logger.info(
            "sync_quotes_all_positions",
            user_id=str(user.id),
            tickers_count=len(tickers_to_sync),
        )

    if not tickers_to_sync:
        return SyncQuotesResponse(
            quotes_updated=0,
            tickers_processed=0,
            message="No tickers to sync. Add positions or provide tickers.",
        )

    # Fetch and save quotes
    start_date = request.start_date if request else None
    end_date = request.end_date if request else None

    try:
        saved_quotes = await quote_service.fetch_and_save_quotes(
            tickers=tickers_to_sync,
            start_date=start_date,
            end_date=end_date,
        )

        return SyncQuotesResponse(
            quotes_updated=len(saved_quotes),
            tickers_processed=len(tickers_to_sync),
            message=f"Successfully synced {len(saved_quotes)} quotes for {len(tickers_to_sync)} tickers",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "sync_quotes_error",
            user_id=str(user.id),
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync quotes: {str(e)}",
        )


@router.get("/{asset_id}", response_model=QuoteHistoryResponse)
async def get_quote_history(
    user: AuthenticatedUser,
    db: DBSession,
    asset_id: UUID,
    start_date: date | None = Query(None, description="Start date filter (inclusive)"),
    end_date: date | None = Query(None, description="End date filter (inclusive)"),
    limit: int = Query(365, ge=1, le=1000, description="Maximum quotes to return"),
) -> QuoteHistoryResponse:
    """
    Get quote history for an asset.

    Returns historical price data ordered by date descending.
    Supports filtering by date range and limiting results.
    """
    # Verify asset exists
    asset_query = select(Asset).where(Asset.id == asset_id)
    asset_result = await db.execute(asset_query)
    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Get quote history
    quote_service = QuoteService(db)
    quotes = await quote_service.get_price_history(
        asset_id=asset_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

    return QuoteHistoryResponse(
        items=[QuoteResponse.model_validate(q) for q in quotes],
        total=len(quotes),
        asset_id=asset_id,
        ticker=asset.ticker,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{asset_id}/latest", response_model=LatestPriceResponse)
async def get_latest_price(
    user: AuthenticatedUser,
    db: DBSession,
    asset_id: UUID,
    use_cache: bool = Query(True, description="Try to get price from cache first"),
) -> LatestPriceResponse:
    """
    Get the latest price for an asset.

    If use_cache is True (default), attempts to retrieve from Redis cache first.
    Falls back to database if not cached.
    """
    # Verify asset exists
    asset_query = select(Asset).where(Asset.id == asset_id)
    asset_result = await db.execute(asset_query)
    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    cached = False
    price: Decimal | None = None
    quote_date: date | None = None
    source: str = "database"

    # Try cache first
    if use_cache:
        cached_price = await get_cached_price(asset_id)
        if cached_price is not None:
            price = cached_price
            cached = True
            source = "cache"
            # Get date from most recent quote for response
            quote_service = QuoteService(db)
            quotes = await quote_service.get_price_history(asset_id, limit=1)
            if quotes:
                quote_date = quotes[0].date

    # Fallback to database
    if price is None:
        quote_service = QuoteService(db)
        quotes = await quote_service.get_price_history(asset_id, limit=1)

        if not quotes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No quotes found for this asset",
            )

        quote = quotes[0]
        price = quote.adjusted_close if quote.adjusted_close else quote.close
        quote_date = quote.date
        source = quote.source

        # Cache the price for future requests
        if use_cache:
            await set_cached_price(asset_id, price)

    return LatestPriceResponse(
        asset_id=asset_id,
        price=price,
        date=quote_date,
        source=source,
        cached=cached,
    )


@router.post("/latest", response_model=LatestPricesResponse)
async def get_latest_prices(
    user: AuthenticatedUser,
    db: DBSession,
    asset_ids: list[UUID],
    use_cache: bool = Query(True, description="Try to get prices from cache first"),
) -> LatestPricesResponse:
    """
    Get latest prices for multiple assets.

    Accepts a list of asset IDs and returns the latest price for each.
    Uses Redis cache for efficient retrieval when available.
    """
    if not asset_ids:
        return LatestPricesResponse(items=[], total=0, cached_count=0)

    if len(asset_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 assets per request",
        )

    # Verify assets exist and get tickers
    asset_query = select(Asset).where(Asset.id.in_(asset_ids))
    asset_result = await db.execute(asset_query)
    assets = {a.id: a for a in asset_result.scalars().all()}

    if not assets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid assets found",
        )

    quote_service = QuoteService(db)
    items: list[LatestPriceResponse] = []
    cached_count = 0

    # Get cached prices first
    cached_prices: dict[UUID, Decimal] = {}
    if use_cache:
        cached_prices = await get_cached_prices(list(assets.keys()))
        cached_count = len(cached_prices)

    # Find which assets need database lookup
    missing_ids = [aid for aid in assets.keys() if aid not in cached_prices]

    # Get prices from database for non-cached assets
    db_prices: dict[UUID, Decimal] = {}
    if missing_ids:
        db_prices = await quote_service.get_latest_prices(missing_ids)

        # Cache the newly fetched prices
        if use_cache and db_prices:
            await set_cached_prices(db_prices)

    # Get dates for response (need to query for this)
    quote_dates: dict[UUID, date] = {}
    quote_sources: dict[UUID, str] = {}

    for asset_id in assets.keys():
        quotes = await quote_service.get_price_history(asset_id, limit=1)
        if quotes:
            quote_dates[asset_id] = quotes[0].date
            quote_sources[asset_id] = quotes[0].source

    # Build response
    for asset_id in assets.keys():
        price = cached_prices.get(asset_id) or db_prices.get(asset_id)
        if price is not None:
            items.append(
                LatestPriceResponse(
                    asset_id=asset_id,
                    price=price,
                    date=quote_dates.get(asset_id),
                    source=quote_sources.get(asset_id, "unknown"),
                    cached=asset_id in cached_prices,
                )
            )

    return LatestPricesResponse(
        items=items,
        total=len(items),
        cached_count=cached_count,
    )
