"""
Portfolio snapshot generation Celery tasks.

Scheduled tasks for daily portfolio snapshot generation.
Runs after NAV calculation (19:00) at 19:30 BRT.
"""

import asyncio
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, distinct, and_

from app.core.logging import get_logger
from app.database import async_session_maker
from app.models import Account, PortfolioSnapshot, Position
from app.services.pnl_service import PnLService
from app.services.quote_service import QuoteService
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="generate_daily_snapshot", max_retries=3)
def generate_daily_snapshot(self, target_date: str | None = None):
    """
    Generate daily portfolio snapshots for all users.

    Scheduled to run at 19:30 BRT after NAV calculation (19:00).

    Args:
        target_date: Optional date string (YYYY-MM-DD). Defaults to today.
    """
    logger.info(
        "generate_daily_snapshot_start",
        target_date=target_date,
    )

    try:
        result = run_async(_generate_snapshots_for_all_users(target_date))
        logger.info(
            "generate_daily_snapshot_complete",
            users_processed=result["users_processed"],
            snapshots_created=result["snapshots_created"],
            errors=result["errors"],
        )
        return result
    except Exception as exc:
        logger.error(
            "generate_daily_snapshot_failed",
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=60)


async def _generate_snapshots_for_all_users(target_date: str | None = None) -> dict:
    """
    Generate portfolio snapshots for all users.

    Returns:
        Dictionary with processing results
    """
    if target_date:
        snap_date = date.fromisoformat(target_date)
    else:
        snap_date = date.today()

    users_processed = 0
    snapshots_created = 0
    errors = []

    async with async_session_maker() as db:
        # Get all unique user IDs that have accounts
        query = select(distinct(Account.user_id)).where(Account.is_active == True)
        result = await db.execute(query)
        user_ids = [row[0] for row in result.fetchall()]

        logger.info(
            "snapshot_generation_users_found",
            user_count=len(user_ids),
        )

        for user_id in user_ids:
            try:
                count = await _generate_snapshot_for_user(db, user_id, snap_date)
                snapshots_created += count
                users_processed += 1

                logger.info(
                    "snapshot_generation_user_complete",
                    user_id=str(user_id),
                    snapshots_count=count,
                )

            except Exception as e:
                error_msg = f"User {user_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    "snapshot_generation_user_error",
                    user_id=str(user_id),
                    error=str(e),
                )

        await db.commit()

    return {
        "users_processed": users_processed,
        "snapshots_created": snapshots_created,
        "errors": errors,
        "date": snap_date.isoformat(),
    }


async def _generate_snapshot_for_user(
    db,
    user_id: UUID,
    snap_date: date,
) -> int:
    """
    Generate portfolio snapshots for a single user.

    Creates both:
    - Consolidated snapshot (account_id = None)
    - Per-account snapshots

    Returns:
        Number of snapshots created
    """
    snapshots_created = 0

    # Get all positions for user
    query = (
        select(Position)
        .join(Position.account)
        .where(Account.user_id == user_id)
        .where(Position.quantity > 0)
    )
    result = await db.execute(query)
    positions = list(result.scalars().all())

    if not positions:
        return 0

    # Get current prices
    asset_ids = list(set(pos.asset_id for pos in positions))
    quote_service = QuoteService(db)
    current_prices = await quote_service.get_prices_at_date(asset_ids, snap_date)

    # Calculate realized P&L
    pnl_service = PnLService(db)
    realized_summary = await pnl_service.calculate_realized_pnl(user_id=user_id)

    # Calculate consolidated snapshot
    total_nav = Decimal("0")
    total_cost = Decimal("0")
    total_unrealized = Decimal("0")

    for pos in positions:
        price = current_prices.get(pos.asset_id)
        if price:
            market_value = pos.quantity * price
            total_nav += market_value
            total_unrealized += market_value - pos.total_cost
        else:
            # Use cost if no price
            total_nav += pos.total_cost

        total_cost += pos.total_cost

    # Create consolidated snapshot (account_id = None)
    consolidated = await _upsert_snapshot(
        db=db,
        user_id=user_id,
        snap_date=snap_date,
        account_id=None,
        nav=total_nav,
        total_cost=total_cost,
        realized_pnl=realized_summary.total_realized_pnl,
        unrealized_pnl=total_unrealized,
    )
    if consolidated:
        snapshots_created += 1

    # Create per-account snapshots
    account_positions: dict[UUID, list[Position]] = {}
    for pos in positions:
        if pos.account_id not in account_positions:
            account_positions[pos.account_id] = []
        account_positions[pos.account_id].append(pos)

    for account_id, acc_positions in account_positions.items():
        acc_nav = Decimal("0")
        acc_cost = Decimal("0")
        acc_unrealized = Decimal("0")

        for pos in acc_positions:
            price = current_prices.get(pos.asset_id)
            if price:
                market_value = pos.quantity * price
                acc_nav += market_value
                acc_unrealized += market_value - pos.total_cost
            else:
                acc_nav += pos.total_cost

            acc_cost += pos.total_cost

        # Get realized P&L for this account
        acc_realized = await pnl_service.calculate_realized_pnl(account_id=account_id)

        snapshot = await _upsert_snapshot(
            db=db,
            user_id=user_id,
            snap_date=snap_date,
            account_id=account_id,
            nav=acc_nav,
            total_cost=acc_cost,
            realized_pnl=acc_realized.total_realized_pnl,
            unrealized_pnl=acc_unrealized,
        )
        if snapshot:
            snapshots_created += 1

    return snapshots_created


async def _upsert_snapshot(
    db,
    user_id: UUID,
    snap_date: date,
    account_id: UUID | None,
    nav: Decimal,
    total_cost: Decimal,
    realized_pnl: Decimal,
    unrealized_pnl: Decimal,
) -> PortfolioSnapshot | None:
    """Insert or update a portfolio snapshot."""
    # Check if exists
    if account_id:
        query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.date == snap_date,
                PortfolioSnapshot.account_id == account_id,
            )
        )
    else:
        query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.date == snap_date,
                PortfolioSnapshot.account_id.is_(None),
            )
        )

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.nav = nav
        existing.total_cost = total_cost
        existing.realized_pnl = realized_pnl
        existing.unrealized_pnl = unrealized_pnl
        await db.flush()
        return existing
    else:
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            date=snap_date,
            account_id=account_id,
            nav=nav,
            total_cost=total_cost,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
        )
        db.add(snapshot)
        await db.flush()
        return snapshot


@celery_app.task(bind=True, name="generate_snapshot_for_user", max_retries=3)
def generate_snapshot_for_user(self, user_id: str, target_date: str | None = None):
    """
    Generate portfolio snapshot for a specific user.

    Can be called on-demand after significant changes.

    Args:
        user_id: User UUID as string
        target_date: Optional date string (YYYY-MM-DD). Defaults to today.
    """
    logger.info(
        "generate_snapshot_for_user_start",
        user_id=user_id,
        target_date=target_date,
    )

    try:
        result = run_async(_generate_single_user_snapshot(user_id, target_date))
        logger.info(
            "generate_snapshot_for_user_complete",
            user_id=user_id,
            snapshots=result.get("snapshots_created"),
        )
        return result
    except Exception as exc:
        logger.error(
            "generate_snapshot_for_user_failed",
            user_id=user_id,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=30)


async def _generate_single_user_snapshot(
    user_id: str,
    target_date: str | None = None,
) -> dict:
    """Generate snapshots for a single user."""
    if target_date:
        snap_date = date.fromisoformat(target_date)
    else:
        snap_date = date.today()

    user_uuid = UUID(user_id)

    async with async_session_maker() as db:
        count = await _generate_snapshot_for_user(db, user_uuid, snap_date)
        await db.commit()

        return {
            "user_id": user_id,
            "date": snap_date.isoformat(),
            "snapshots_created": count,
        }
