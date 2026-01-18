"""
Quote service for fetching and managing asset prices.

Provides functions to:
- Fetch quotes from Yahoo Finance and persist to database
- Get latest prices for assets
- Get price history
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.integrations.yfinance_client import (
    QuoteData,
    fetch_quote,
    fetch_quotes_batch,
)
from app.models import Asset, Quote
from app.schemas.enums import AssetType

logger = get_logger(__name__)


class QuoteService:
    """Service for managing quotes and prices."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Fetch & Save Methods (integration with yfinance)
    # -------------------------------------------------------------------------

    async def fetch_and_save_quotes(
        self,
        tickers: list[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Quote]:
        """
        Fetch quotes from Yahoo Finance and save to database.

        Args:
            tickers: List of ticker symbols to fetch
            start_date: Start date for historical data (defaults to today)
            end_date: End date for historical data (defaults to today)

        Returns:
            List of saved Quote objects

        Raises:
            ValueError: If no valid tickers are provided
        """
        if not tickers:
            raise ValueError("At least one ticker must be provided")

        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date

        logger.info(
            "quote_service_fetch_start",
            tickers_count=len(tickers),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        # Fetch quotes from Yahoo Finance
        quotes_by_ticker = await fetch_quotes_batch(tickers, start_date, end_date)

        # Get or create assets for all tickers
        ticker_to_asset = await self._get_or_create_assets(list(quotes_by_ticker.keys()))

        # Save quotes to database
        saved_quotes: list[Quote] = []

        for ticker, quote_data_list in quotes_by_ticker.items():
            if not quote_data_list:
                continue

            asset = ticker_to_asset.get(ticker.upper())
            if not asset:
                logger.warning("quote_service_asset_not_found", ticker=ticker)
                continue

            for quote_data in quote_data_list:
                quote = await self._upsert_quote(asset.id, quote_data)
                if quote:
                    saved_quotes.append(quote)

        await self.db.commit()

        logger.info(
            "quote_service_fetch_complete",
            tickers_count=len(tickers),
            quotes_saved=len(saved_quotes),
        )

        return saved_quotes

    async def _get_or_create_assets(
        self,
        tickers: list[str],
    ) -> dict[str, Asset]:
        """
        Get existing assets by ticker, or create minimal asset records.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to Asset
        """
        if not tickers:
            return {}

        # Normalize tickers to uppercase
        normalized_tickers = [t.upper() for t in tickers]

        # Query existing assets
        query = select(Asset).where(Asset.ticker.in_(normalized_tickers))
        result = await self.db.execute(query)
        existing_assets = {asset.ticker: asset for asset in result.scalars().all()}

        # Assets to be created (not found in database)
        missing_tickers = set(normalized_tickers) - set(existing_assets.keys())

        if missing_tickers:
            logger.info(
                "quote_service_creating_assets",
                missing_count=len(missing_tickers),
                tickers=list(missing_tickers),
            )

            # Create minimal asset records for missing tickers
            for ticker in missing_tickers:
                asset_type = self._infer_asset_type(ticker)
                asset = Asset(
                    ticker=ticker,
                    name=ticker,  # Will be updated later with proper name
                    asset_type=asset_type,
                    currency="BRL" if self._is_brazilian_ticker(ticker) else "USD",
                    exchange="B3" if self._is_brazilian_ticker(ticker) else None,
                )
                self.db.add(asset)
                existing_assets[ticker] = asset

            await self.db.flush()

        return existing_assets

    async def _upsert_quote(
        self,
        asset_id: UUID,
        quote_data: QuoteData,
    ) -> Quote | None:
        """
        Insert or update a quote in the database.

        Uses PostgreSQL upsert (INSERT ... ON CONFLICT UPDATE).

        Args:
            asset_id: Asset UUID
            quote_data: Quote data from Yahoo Finance

        Returns:
            Upserted Quote object or None if failed
        """
        try:
            stmt = pg_insert(Quote).values(
                asset_id=asset_id,
                date=quote_data.date,
                open=quote_data.open,
                high=quote_data.high,
                low=quote_data.low,
                close=quote_data.close,
                adjusted_close=quote_data.adjusted_close,
                volume=quote_data.volume,
                source="yfinance",
            )

            # On conflict, update the values
            stmt = stmt.on_conflict_do_update(
                constraint="uq_quotes_asset_date",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "adjusted_close": stmt.excluded.adjusted_close,
                    "volume": stmt.excluded.volume,
                    "source": stmt.excluded.source,
                },
            )

            await self.db.execute(stmt)

            # Fetch the upserted record
            query = select(Quote).where(
                and_(
                    Quote.asset_id == asset_id,
                    Quote.date == quote_data.date,
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                "quote_service_upsert_error",
                asset_id=str(asset_id),
                date=quote_data.date.isoformat(),
                error=str(e),
            )
            return None

    def _is_brazilian_ticker(self, ticker: str) -> bool:
        """Check if a ticker looks like a Brazilian (B3) ticker."""
        ticker = ticker.upper()
        if len(ticker) >= 4 and len(ticker) <= 6:
            if ticker[-1].isdigit():
                letter_part = ticker.rstrip("0123456789")
                if len(letter_part) >= 3 and letter_part.isalpha():
                    return True
        return False

    def _infer_asset_type(self, ticker: str) -> AssetType:
        """
        Infer asset type from ticker symbol.

        Brazilian conventions:
        - Ending in 11: FII (Fundo Imobiliario) or Unit
        - Ending in 3, 4, 5, 6: Stock (ON, PN, PNA, PNB)
        - Ending in 34, 35: BDR
        """
        ticker = ticker.upper()

        if not self._is_brazilian_ticker(ticker):
            return AssetType.STOCK

        # Get the numeric suffix
        numeric_part = ""
        for char in reversed(ticker):
            if char.isdigit():
                numeric_part = char + numeric_part
            else:
                break

        if numeric_part:
            num = int(numeric_part)

            # FII typically ends in 11
            if num == 11:
                # Check if it looks like FII (4 letters + 11)
                letter_part = ticker.rstrip("0123456789")
                if len(letter_part) == 4:
                    return AssetType.FII

            # BDR typically ends in 34 or 35
            if num in (34, 35):
                return AssetType.BDR

            # FIAGRO typically has specific patterns
            if ticker.startswith("FIAG") or "AGRO" in ticker:
                return AssetType.FIAGRO

        return AssetType.STOCK

    # -------------------------------------------------------------------------
    # Query Methods (get prices from database)
    # -------------------------------------------------------------------------

    async def get_latest_prices(
        self,
        asset_ids: list[UUID],
    ) -> dict[UUID, Decimal]:
        """
        Get the latest price for each asset.

        Fetches the most recent quote (by date) for each asset ID.

        Args:
            asset_ids: List of asset UUIDs to get prices for

        Returns:
            Dictionary mapping asset_id -> latest close price
        """
        if not asset_ids:
            return {}

        logger.debug(
            "get_latest_prices",
            asset_count=len(asset_ids),
        )

        # Subquery to get the max date for each asset
        max_date_subq = (
            select(
                Quote.asset_id,
                func.max(Quote.date).label("max_date"),
            )
            .where(Quote.asset_id.in_(asset_ids))
            .group_by(Quote.asset_id)
            .subquery()
        )

        # Join to get the actual quote records for those dates
        query = (
            select(Quote)
            .join(
                max_date_subq,
                and_(
                    Quote.asset_id == max_date_subq.c.asset_id,
                    Quote.date == max_date_subq.c.max_date,
                ),
            )
        )

        result = await self.db.execute(query)
        quotes = result.scalars().all()

        prices: dict[UUID, Decimal] = {}
        for quote in quotes:
            # Prefer adjusted_close if available, otherwise use close
            price = quote.adjusted_close if quote.adjusted_close else quote.close
            prices[quote.asset_id] = price

        logger.info(
            "latest_prices_fetched",
            requested=len(asset_ids),
            found=len(prices),
        )

        return prices

    async def get_latest_price(
        self,
        asset_id: UUID,
    ) -> Decimal | None:
        """
        Get the latest price for a single asset.

        Args:
            asset_id: Asset UUID

        Returns:
            Latest close price or None if not found
        """
        prices = await self.get_latest_prices([asset_id])
        return prices.get(asset_id)

    async def get_price_history(
        self,
        asset_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 365,
    ) -> list[Quote]:
        """
        Get price history for an asset.

        Args:
            asset_id: Asset UUID
            start_date: Start date filter (inclusive)
            end_date: End date filter (inclusive)
            limit: Maximum number of quotes to return

        Returns:
            List of Quote objects ordered by date descending
        """
        query = (
            select(Quote)
            .where(Quote.asset_id == asset_id)
            .order_by(Quote.date.desc())
            .limit(limit)
        )

        if start_date:
            query = query.where(Quote.date >= start_date)
        if end_date:
            query = query.where(Quote.date <= end_date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_price_at_date(
        self,
        asset_id: UUID,
        target_date: date,
    ) -> Decimal | None:
        """
        Get the price for an asset on a specific date.

        If no quote exists for that exact date, returns the most recent
        quote before that date.

        Args:
            asset_id: Asset UUID
            target_date: Target date

        Returns:
            Close price or None if not found
        """
        query = (
            select(Quote)
            .where(
                and_(
                    Quote.asset_id == asset_id,
                    Quote.date <= target_date,
                )
            )
            .order_by(Quote.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        quote = result.scalar_one_or_none()

        if quote:
            return quote.adjusted_close if quote.adjusted_close else quote.close
        return None

    async def get_prices_at_date(
        self,
        asset_ids: list[UUID],
        target_date: date,
    ) -> dict[UUID, Decimal]:
        """
        Get prices for multiple assets at a specific date.

        For each asset, returns the quote on that date or the most recent
        quote before that date.

        Args:
            asset_ids: List of asset UUIDs
            target_date: Target date

        Returns:
            Dictionary mapping asset_id -> price
        """
        if not asset_ids:
            return {}

        # For each asset, get the max date <= target_date
        max_date_subq = (
            select(
                Quote.asset_id,
                func.max(Quote.date).label("max_date"),
            )
            .where(
                and_(
                    Quote.asset_id.in_(asset_ids),
                    Quote.date <= target_date,
                )
            )
            .group_by(Quote.asset_id)
            .subquery()
        )

        query = (
            select(Quote)
            .join(
                max_date_subq,
                and_(
                    Quote.asset_id == max_date_subq.c.asset_id,
                    Quote.date == max_date_subq.c.max_date,
                ),
            )
        )

        result = await self.db.execute(query)
        quotes = result.scalars().all()

        prices: dict[UUID, Decimal] = {}
        for quote in quotes:
            price = quote.adjusted_close if quote.adjusted_close else quote.close
            prices[quote.asset_id] = price

        return prices


async def get_latest_prices(
    db: AsyncSession,
    asset_ids: list[UUID],
) -> dict[UUID, Decimal]:
    """
    Utility function to get latest prices for multiple assets.

    Args:
        db: Database session
        asset_ids: List of asset UUIDs

    Returns:
        Dictionary mapping asset_id -> latest price
    """
    service = QuoteService(db)
    return await service.get_latest_prices(asset_ids)


async def fetch_quotes(
    db: AsyncSession,
    tickers: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Quote]:
    """
    Utility function to fetch and save quotes from Yahoo Finance.

    This is a convenience wrapper around QuoteService for use
    in Celery tasks and other contexts.

    Args:
        db: Database session
        tickers: List of ticker symbols
        start_date: Start date (defaults to today)
        end_date: End date (defaults to today)

    Returns:
        List of saved Quote objects
    """
    service = QuoteService(db)
    return await service.fetch_and_save_quotes(tickers, start_date, end_date)
