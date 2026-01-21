#!/usr/bin/env python3
"""
Backfill historical NAV and FundShare records.

This script reconstructs position history and calculates daily NAV values
from May 2021 to today, creating FundShare records for fund performance tracking.

Usage:
    python -m scripts.backfill_nav

Or from backend directory:
    python scripts/backfill_nav.py
"""

import asyncio
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import (
    Account,
    Asset,
    CashFlow,
    FundShare,
    Quote,
    Transaction,
)
from app.schemas.enums import CashFlowType, PositionType, TransactionType


# Backfill start date
START_DATE = date(2021, 5, 1)

# Initial share value (from nav_service.py)
INITIAL_SHARE_VALUE = Decimal("100.00000000")


@dataclass
class PositionState:
    """Track position state for an asset."""

    asset_id: UUID
    quantity: Decimal
    avg_price: Decimal
    total_cost: Decimal
    position_type: PositionType


@dataclass
class DailyNAV:
    """Daily NAV calculation result."""

    date: date
    nav: Decimal
    market_value: Decimal
    long_value: Decimal
    short_value: Decimal
    cash_balance: Decimal
    positions_count: int


async def get_user_id(db: AsyncSession) -> UUID | None:
    """Get the single user ID from accounts (assumes single-user system)."""
    query = select(distinct(Account.user_id))
    result = await db.execute(query)
    user_ids = list(result.scalars().all())

    if not user_ids:
        return None

    if len(user_ids) > 1:
        print(f"Warning: Multiple users found: {user_ids}")
        print("Using first user")

    return user_ids[0]


async def get_trading_days(db: AsyncSession, start: date, end: date) -> list[date]:
    """
    Get all trading days with quote data between start and end dates.

    Returns dates in ascending order.
    """
    query = (
        select(distinct(Quote.date))
        .where(and_(Quote.date >= start, Quote.date <= end))
        .order_by(Quote.date)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_transactions_ordered(
    db: AsyncSession, user_id: UUID
) -> list[Transaction]:
    """Get all transactions for user ordered by date."""
    query = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id)
        .order_by(Transaction.executed_at)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_all_cash_flows_ordered(
    db: AsyncSession, user_id: UUID
) -> list[CashFlow]:
    """Get all cash flows for user ordered by date."""
    query = (
        select(CashFlow)
        .join(Account, CashFlow.account_id == Account.id)
        .where(Account.user_id == user_id)
        .order_by(CashFlow.executed_at)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_asset_prices_at_date(
    db: AsyncSession, asset_ids: list[UUID], target_date: date
) -> dict[UUID, Decimal]:
    """
    Get prices for assets at a specific date.

    Uses the most recent price on or before the target date.
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

    query = select(Quote).join(
        max_date_subq,
        and_(
            Quote.asset_id == max_date_subq.c.asset_id,
            Quote.date == max_date_subq.c.max_date,
        ),
    )

    result = await db.execute(query)
    quotes = result.scalars().all()

    prices: dict[UUID, Decimal] = {}
    for quote in quotes:
        price = quote.adjusted_close if quote.adjusted_close else quote.close
        prices[quote.asset_id] = price

    return prices


def apply_transaction_to_positions(
    positions: dict[UUID, PositionState],
    txn: Transaction,
) -> None:
    """
    Apply a transaction to the position state.

    Implements FIFO position netting for long/short positions.
    """
    asset_id = txn.asset_id
    quantity = txn.quantity
    price = txn.price

    # Get or create position state
    if asset_id not in positions:
        positions[asset_id] = PositionState(
            asset_id=asset_id,
            quantity=Decimal("0"),
            avg_price=Decimal("0"),
            total_cost=Decimal("0"),
            position_type=PositionType.LONG,
        )

    pos = positions[asset_id]

    if txn.type == TransactionType.BUY:
        # Buying increases long position or reduces short position
        if pos.position_type == PositionType.SHORT and pos.quantity > 0:
            # Closing short position
            if quantity >= pos.quantity:
                # Fully closed, may flip to long
                remaining = quantity - pos.quantity
                pos.quantity = remaining
                if remaining > 0:
                    pos.position_type = PositionType.LONG
                    pos.avg_price = price
                    pos.total_cost = remaining * price
                else:
                    pos.avg_price = Decimal("0")
                    pos.total_cost = Decimal("0")
            else:
                # Partial close
                pos.quantity -= quantity
        else:
            # Adding to long position
            new_quantity = pos.quantity + quantity
            new_cost = pos.total_cost + (quantity * price)
            pos.quantity = new_quantity
            pos.total_cost = new_cost
            pos.avg_price = new_cost / new_quantity if new_quantity > 0 else Decimal("0")
            pos.position_type = PositionType.LONG

    elif txn.type == TransactionType.SELL:
        # Selling decreases long position or increases short position
        if pos.position_type == PositionType.LONG and pos.quantity > 0:
            # Closing long position
            if quantity >= pos.quantity:
                # Fully closed, may flip to short
                remaining = quantity - pos.quantity
                pos.quantity = remaining
                if remaining > 0:
                    pos.position_type = PositionType.SHORT
                    pos.avg_price = price
                    pos.total_cost = remaining * price
                else:
                    pos.avg_price = Decimal("0")
                    pos.total_cost = Decimal("0")
            else:
                # Partial close
                pos.quantity -= quantity
                pos.total_cost = pos.quantity * pos.avg_price
        else:
            # Adding to short position
            new_quantity = pos.quantity + quantity
            new_cost = pos.total_cost + (quantity * price)
            pos.quantity = new_quantity
            pos.total_cost = new_cost
            pos.avg_price = new_cost / new_quantity if new_quantity > 0 else Decimal("0")
            pos.position_type = PositionType.SHORT

    # Handle splits/bonus
    elif txn.type in (TransactionType.SPLIT, TransactionType.BONUS):
        if pos.quantity > 0:
            pos.quantity += quantity
            # Adjust avg price for split
            if pos.quantity > 0:
                pos.avg_price = pos.total_cost / pos.quantity


def calculate_cash_balance(
    cash_flows: list[CashFlow],
    transactions: list[Transaction],
    as_of: date
) -> Decimal:
    """
    Calculate cash balance from cash flows and transactions up to a given date.

    Cash balance = deposits - withdrawals - buy_costs + sell_proceeds
    """
    balance = Decimal("0")

    # Process cash flows (deposits/withdrawals)
    for cf in cash_flows:
        cf_date = cf.executed_at.date() if isinstance(cf.executed_at, datetime) else cf.executed_at
        if cf_date > as_of:
            break

        amount = cf.amount * cf.exchange_rate
        if cf.type == CashFlowType.DEPOSIT:
            balance += amount
        elif cf.type == CashFlowType.WITHDRAWAL:
            balance -= amount

    # Process transactions (buys reduce cash, sells increase cash)
    for txn in transactions:
        txn_date = txn.executed_at.date() if isinstance(txn.executed_at, datetime) else txn.executed_at
        if txn_date > as_of:
            break

        # Calculate transaction value including fees
        txn_value = txn.quantity * txn.price
        fees = txn.fees or Decimal("0")

        if txn.type == TransactionType.BUY:
            # Buying uses cash
            balance -= (txn_value + fees)
        elif txn.type == TransactionType.SELL:
            # Selling generates cash
            balance += (txn_value - fees)

    return balance


def calculate_nav(
    positions: dict[UUID, PositionState],
    prices: dict[UUID, Decimal],
    cash_balance: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Calculate NAV from positions and prices.

    Returns: (nav, market_value, long_value, short_value)
    """
    long_value = Decimal("0")
    short_value = Decimal("0")

    for asset_id, pos in positions.items():
        if pos.quantity <= 0:
            continue

        price = prices.get(asset_id)
        if price is not None:
            market_value = pos.quantity * price
        else:
            # Use cost basis if no price available
            market_value = pos.total_cost

        if pos.position_type == PositionType.SHORT:
            short_value += market_value
        else:
            long_value += market_value

    total_market_value = long_value - short_value
    nav = total_market_value + cash_balance

    return nav, total_market_value, long_value, short_value


async def upsert_fund_share(
    db: AsyncSession,
    user_id: UUID,
    target_date: date,
    nav: Decimal,
    shares_outstanding: Decimal,
    share_value: Decimal,
    daily_return: Decimal | None,
    cumulative_return: Decimal | None,
) -> FundShare:
    """Insert or update a FundShare record."""
    # Check if record exists
    query = select(FundShare).where(
        and_(
            FundShare.user_id == user_id,
            FundShare.date == target_date,
        )
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.nav = nav
        existing.shares_outstanding = shares_outstanding
        existing.share_value = share_value
        existing.daily_return = daily_return
        existing.cumulative_return = cumulative_return
        return existing
    else:
        fund_share = FundShare(
            user_id=user_id,
            date=target_date,
            nav=nav,
            shares_outstanding=shares_outstanding,
            share_value=share_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
        )
        db.add(fund_share)
        return fund_share


async def update_cash_flow_shares(
    db: AsyncSession,
    cash_flow: CashFlow,
    shares_affected: Decimal,
) -> None:
    """Update shares_affected on a cash flow."""
    cash_flow.shares_affected = shares_affected


async def backfill_nav():
    """Backfill historical NAV and FundShare records."""
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("BACKFILL HISTORICAL NAV")
        print("=" * 70)
        print(f"Start date: {START_DATE}")
        print(f"End date: {date.today()}")
        print()

        # Get user ID
        user_id = await get_user_id(db)
        if not user_id:
            print("No accounts found. Cannot backfill NAV.")
            return

        print(f"User ID: {user_id}")
        print()

        # Get all trading days
        trading_days = await get_trading_days(db, START_DATE, date.today())
        if not trading_days:
            print("No trading days with quotes found. Run backfill_quotes.py first.")
            return

        print(f"Found {len(trading_days)} trading days with quotes")
        print(f"  First: {trading_days[0]}")
        print(f"  Last: {trading_days[-1]}")
        print()

        # Get all transactions and cash flows
        transactions = await get_all_transactions_ordered(db, user_id)
        cash_flows = await get_all_cash_flows_ordered(db, user_id)

        print(f"Loaded {len(transactions)} transactions")
        print(f"Loaded {len(cash_flows)} cash flows")
        print()

        # Group cash flows by date for easy lookup
        cash_flows_by_date: dict[date, list[CashFlow]] = defaultdict(list)
        for cf in cash_flows:
            cf_date = cf.executed_at.date() if isinstance(cf.executed_at, datetime) else cf.executed_at
            cash_flows_by_date[cf_date].append(cf)

        # Track position state as we replay transactions
        positions: dict[UUID, PositionState] = {}
        txn_index = 0  # Current transaction index

        # Track fund share state
        shares_outstanding = Decimal("0")
        prev_share_value: Decimal | None = None

        # Process each trading day
        fund_shares_created = 0
        cash_flows_updated = 0

        print("Processing trading days...")

        for i, current_date in enumerate(trading_days):
            # Apply all transactions up to and including current_date
            while txn_index < len(transactions):
                txn = transactions[txn_index]
                txn_date = txn.executed_at.date() if isinstance(txn.executed_at, datetime) else txn.executed_at

                if txn_date > current_date:
                    break

                apply_transaction_to_positions(positions, txn)
                txn_index += 1

            # Calculate cash balance up to current_date
            cash_balance = calculate_cash_balance(cash_flows, transactions, current_date)

            # Get prices for all positions
            asset_ids = [
                asset_id for asset_id, pos in positions.items()
                if pos.quantity > 0
            ]
            prices = await get_asset_prices_at_date(db, asset_ids, current_date)

            # Calculate NAV
            nav, market_value, long_value, short_value = calculate_nav(
                positions, prices, cash_balance
            )

            # Skip days with zero NAV
            if nav <= 0:
                continue

            # Process cash flows for this day (issue/redeem shares)
            day_cash_flows = cash_flows_by_date.get(current_date, [])

            for cf in day_cash_flows:
                if cf.type == CashFlowType.DEPOSIT:
                    # Issue new shares
                    share_value_for_issue = prev_share_value or INITIAL_SHARE_VALUE
                    new_shares = (cf.amount * cf.exchange_rate) / share_value_for_issue
                    shares_outstanding += new_shares

                    await update_cash_flow_shares(db, cf, new_shares)
                    cash_flows_updated += 1

                elif cf.type == CashFlowType.WITHDRAWAL:
                    # Redeem shares
                    share_value_for_redeem = prev_share_value or INITIAL_SHARE_VALUE
                    shares_to_redeem = (cf.amount * cf.exchange_rate) / share_value_for_redeem
                    shares_outstanding -= shares_to_redeem

                    await update_cash_flow_shares(db, cf, -shares_to_redeem)
                    cash_flows_updated += 1

            # If no shares outstanding yet, initialize from NAV
            if shares_outstanding <= 0:
                shares_outstanding = nav / INITIAL_SHARE_VALUE

            # Calculate share value
            share_value = nav / shares_outstanding if shares_outstanding > 0 else INITIAL_SHARE_VALUE

            # Calculate returns
            daily_return: Decimal | None = None
            if prev_share_value is not None and prev_share_value > 0:
                daily_return = (share_value - prev_share_value) / prev_share_value

            cumulative_return = (share_value - INITIAL_SHARE_VALUE) / INITIAL_SHARE_VALUE

            # Create/update FundShare record
            await upsert_fund_share(
                db=db,
                user_id=user_id,
                target_date=current_date,
                nav=nav,
                shares_outstanding=shares_outstanding,
                share_value=share_value,
                daily_return=daily_return,
                cumulative_return=cumulative_return,
            )
            fund_shares_created += 1

            # Update previous share value for next iteration
            prev_share_value = share_value

            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(trading_days)} days...")

        # Commit all changes
        await db.commit()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Trading days processed: {len(trading_days)}")
        print(f"FundShare records created/updated: {fund_shares_created}")
        print(f"CashFlow records updated with shares: {cash_flows_updated}")

        # Verify counts
        count_query = select(func.count()).select_from(FundShare).where(
            FundShare.user_id == user_id
        )
        count_result = await db.execute(count_query)
        total_fund_shares = count_result.scalar()

        print(f"\nTotal FundShare records in database: {total_fund_shares}")

        # Show latest FundShare
        latest_query = (
            select(FundShare)
            .where(FundShare.user_id == user_id)
            .order_by(FundShare.date.desc())
            .limit(1)
        )
        latest_result = await db.execute(latest_query)
        latest = latest_result.scalar_one_or_none()

        if latest:
            print("\nLatest FundShare:")
            print(f"  Date: {latest.date}")
            print(f"  NAV: R$ {latest.nav:,.2f}")
            print(f"  Shares Outstanding: {latest.shares_outstanding:,.8f}")
            print(f"  Share Value: R$ {latest.share_value:,.8f}")
            print(f"  Daily Return: {latest.daily_return * 100 if latest.daily_return else 'N/A':.4f}%")
            print(f"  Cumulative Return: {latest.cumulative_return * 100 if latest.cumulative_return else 'N/A':.2f}%")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(backfill_nav())
