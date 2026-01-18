"""
Celery tasks for quote synchronization.

Provides automated quote fetching from Yahoo Finance for all active assets.
"""

import asyncio
from datetime import date

from sqlalchemy import select

from app.core.logging import get_logger
from app.database import async_session_factory
from app.models import Asset
from app.services.quote_service import QuoteService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="sync_all_quotes",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 minutes
)
def sync_all_quotes(self) -> dict:
    """
    Celery task to synchronize quotes for all active assets.

    Fetches current quotes from Yahoo Finance for all assets marked as
    is_active=True in the database and saves them.

    Returns:
        Dictionary with sync results:
        - success: bool
        - tickers_count: int
        - quotes_saved: int
        - error: str | None
    """
    logger.info(
        "task_sync_all_quotes_start",
        attempt=self.request.retries + 1,
    )

    async def _sync_quotes():
        async with async_session_factory() as session:
            try:
                # Fetch all active tickers from database
                query = select(Asset.ticker).where(Asset.is_active == True)
                result = await session.execute(query)
                tickers = [row[0] for row in result.fetchall()]

                if not tickers:
                    logger.info("task_sync_all_quotes_no_tickers")
                    return {
                        "success": True,
                        "tickers_count": 0,
                        "quotes_saved": 0,
                        "error": None,
                    }

                logger.info(
                    "task_sync_all_quotes_fetching",
                    tickers_count=len(tickers),
                    tickers=tickers[:10],  # Log first 10 tickers
                )

                # Use QuoteService to fetch and save quotes
                service = QuoteService(session)
                quotes = await service.fetch_and_save_quotes(
                    tickers=tickers,
                    start_date=date.today(),
                    end_date=date.today(),
                )

                return {
                    "success": True,
                    "tickers_count": len(tickers),
                    "quotes_saved": len(quotes),
                    "error": None,
                }

            except ValueError as e:
                # Don't retry for validation errors
                logger.warning(
                    "task_sync_all_quotes_validation_error",
                    error=str(e),
                )
                return {
                    "success": False,
                    "tickers_count": 0,
                    "quotes_saved": 0,
                    "error": str(e),
                }

    try:
        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_sync_quotes())
        finally:
            loop.close()

        logger.info(
            "task_sync_all_quotes_complete",
            success=result["success"],
            tickers_count=result["tickers_count"],
            quotes_saved=result["quotes_saved"],
        )

        return result

    except Exception as e:
        logger.error(
            "task_sync_all_quotes_error",
            error=str(e),
            attempt=self.request.retries + 1,
        )
        raise


@celery_app.task(
    name="sync_quotes_for_tickers",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def sync_quotes_for_tickers(
    self,
    tickers: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Celery task to synchronize quotes for specific tickers.

    This task is useful for manual sync requests from the API.

    Args:
        tickers: List of ticker symbols to fetch
        start_date: Start date in ISO format (YYYY-MM-DD), defaults to today
        end_date: End date in ISO format (YYYY-MM-DD), defaults to today

    Returns:
        Dictionary with sync results
    """
    logger.info(
        "task_sync_quotes_for_tickers_start",
        tickers_count=len(tickers),
        tickers=tickers[:10],
        start_date=start_date,
        end_date=end_date,
        attempt=self.request.retries + 1,
    )

    # Parse dates
    parsed_start = date.fromisoformat(start_date) if start_date else date.today()
    parsed_end = date.fromisoformat(end_date) if end_date else date.today()

    async def _sync_quotes():
        async with async_session_factory() as session:
            try:
                service = QuoteService(session)
                quotes = await service.fetch_and_save_quotes(
                    tickers=tickers,
                    start_date=parsed_start,
                    end_date=parsed_end,
                )

                return {
                    "success": True,
                    "tickers_count": len(tickers),
                    "quotes_saved": len(quotes),
                    "error": None,
                }

            except ValueError as e:
                logger.warning(
                    "task_sync_quotes_for_tickers_validation_error",
                    error=str(e),
                )
                return {
                    "success": False,
                    "tickers_count": len(tickers),
                    "quotes_saved": 0,
                    "error": str(e),
                }

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_sync_quotes())
        finally:
            loop.close()

        logger.info(
            "task_sync_quotes_for_tickers_complete",
            success=result["success"],
            tickers_count=result["tickers_count"],
            quotes_saved=result["quotes_saved"],
        )

        return result

    except Exception as e:
        logger.error(
            "task_sync_quotes_for_tickers_error",
            error=str(e),
            tickers=tickers[:10],
        )
        raise
