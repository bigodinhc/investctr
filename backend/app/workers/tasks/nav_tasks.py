"""
NAV calculation Celery tasks.

Scheduled tasks for daily NAV calculation and fund share generation.
Runs after quote sync (18:30) at 19:00 BRT.
"""

import asyncio
from datetime import date
from uuid import UUID

from app.core.logging import get_logger
from app.database import async_session_maker
from app.models import Account
from app.services.nav_service import NAVService
from app.workers.celery_app import celery_app
from sqlalchemy import select, distinct

logger = get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="calculate_daily_nav", max_retries=3)
def calculate_daily_nav(self, target_date: str | None = None):
    """
    Calculate daily NAV for all users with positions.

    Scheduled to run at 19:00 BRT after quote sync (18:30).

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to today.
    """
    logger.info(
        "calculate_daily_nav_start",
        target_date=target_date,
    )

    try:
        result = run_async(_calculate_nav_for_all_users(target_date))
        logger.info(
            "calculate_daily_nav_complete",
            users_processed=result["users_processed"],
            shares_created=result["shares_created"],
            errors=result["errors"],
        )
        return result
    except Exception as exc:
        logger.error(
            "calculate_daily_nav_failed",
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=60)


async def _calculate_nav_for_all_users(target_date: str | None = None) -> dict:
    """
    Calculate NAV for all users with positions.

    Returns:
        Dictionary with processing results
    """
    if target_date:
        calc_date = date.fromisoformat(target_date)
    else:
        calc_date = date.today()

    users_processed = 0
    shares_created = 0
    errors = []

    async with async_session_maker() as db:
        # Get all unique user IDs that have accounts
        query = select(distinct(Account.user_id)).where(Account.is_active == True)
        result = await db.execute(query)
        user_ids = [row[0] for row in result.fetchall()]

        logger.info(
            "nav_calculation_users_found",
            user_count=len(user_ids),
        )

        nav_service = NAVService(db)

        for user_id in user_ids:
            try:
                fund_share = await nav_service.create_daily_fund_share(
                    user_id=user_id,
                    target_date=calc_date,
                )

                if fund_share:
                    shares_created += 1
                    logger.info(
                        "nav_calculation_user_complete",
                        user_id=str(user_id),
                        nav=str(fund_share.nav),
                        share_value=str(fund_share.share_value),
                    )
                else:
                    logger.info(
                        "nav_calculation_user_skip",
                        user_id=str(user_id),
                        reason="zero_nav",
                    )

                users_processed += 1

            except Exception as e:
                error_msg = f"User {user_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    "nav_calculation_user_error",
                    user_id=str(user_id),
                    error=str(e),
                )

        await db.commit()

    return {
        "users_processed": users_processed,
        "shares_created": shares_created,
        "errors": errors,
        "date": calc_date.isoformat(),
    }


@celery_app.task(bind=True, name="calculate_nav_for_user", max_retries=3)
def calculate_nav_for_user(self, user_id: str, target_date: str | None = None):
    """
    Calculate NAV for a specific user.

    Can be called on-demand after cash flow events.

    Args:
        user_id: User UUID as string
        target_date: Optional date string (YYYY-MM-DD). Defaults to today.
    """
    logger.info(
        "calculate_nav_for_user_start",
        user_id=user_id,
        target_date=target_date,
    )

    try:
        result = run_async(_calculate_nav_for_single_user(user_id, target_date))
        logger.info(
            "calculate_nav_for_user_complete",
            user_id=user_id,
            nav=result.get("nav"),
        )
        return result
    except Exception as exc:
        logger.error(
            "calculate_nav_for_user_failed",
            user_id=user_id,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30)


async def _calculate_nav_for_single_user(
    user_id: str,
    target_date: str | None = None,
) -> dict:
    """Calculate NAV for a single user."""
    if target_date:
        calc_date = date.fromisoformat(target_date)
    else:
        calc_date = date.today()

    user_uuid = UUID(user_id)

    async with async_session_maker() as db:
        nav_service = NAVService(db)
        fund_share = await nav_service.create_daily_fund_share(
            user_id=user_uuid,
            target_date=calc_date,
        )

        await db.commit()

        if fund_share:
            return {
                "user_id": user_id,
                "date": calc_date.isoformat(),
                "nav": str(fund_share.nav),
                "share_value": str(fund_share.share_value),
                "shares_outstanding": str(fund_share.shares_outstanding),
            }
        else:
            return {
                "user_id": user_id,
                "date": calc_date.isoformat(),
                "nav": None,
                "error": "Could not calculate NAV (zero NAV or no positions)",
            }
