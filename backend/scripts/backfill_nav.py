#!/usr/bin/env python3
"""
Backfill historical NAV and FundShare records using PortfolioSnapshot as source of truth.

This script creates FundShare records for fund performance tracking by:
1. Using PortfolioSnapshot NAV (from statements) as the source of truth for end-of-month dates
2. Interpolating daily NAV between snapshots by adjusting only the renda_variavel (stocks)
   portion with market prices, keeping fixed income and funds constant

The interpolation formula for days between snapshots:
    NAV(date) = Previous_snapshot.nav - Previous_snapshot.renda_variavel + RV_market_value(date)

Where RV_market_value(date) = sum of stock positions × market prices on that date.

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
    PortfolioSnapshot,
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
class SnapshotData:
    """Snapshot data for interpolation."""

    date: date
    nav: Decimal
    renda_fixa: Decimal
    fundos_investimento: Decimal
    renda_variavel: Decimal
    derivativos: Decimal
    conta_corrente: Decimal
    coe: Decimal


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


async def get_portfolio_snapshots(
    db: AsyncSession, user_id: UUID
) -> dict[date, SnapshotData]:
    """
    Get all portfolio snapshots aggregated by date.

    IMPORTANT: We sum snapshots from individual accounts (account_id IS NOT NULL)
    to get the consolidated view with breakdowns. We do NOT use the consolidated
    snapshots (account_id IS NULL) because they lack breakdown fields.
    """
    # Get only per-account snapshots (not consolidated ones)
    query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.user_id == user_id)
        .where(PortfolioSnapshot.account_id.isnot(None))  # Only per-account snapshots
        .order_by(PortfolioSnapshot.date)
    )
    result = await db.execute(query)
    snapshots = list(result.scalars().all())

    # Aggregate snapshots by date (sum all accounts for each date)
    snapshot_map: dict[date, SnapshotData] = {}
    for snap in snapshots:
        if snap.date not in snapshot_map:
            snapshot_map[snap.date] = SnapshotData(
                date=snap.date,
                nav=Decimal("0"),
                renda_fixa=Decimal("0"),
                fundos_investimento=Decimal("0"),
                renda_variavel=Decimal("0"),
                derivativos=Decimal("0"),
                conta_corrente=Decimal("0"),
                coe=Decimal("0"),
            )

        # Add this account's values to the aggregate
        existing = snapshot_map[snap.date]
        snapshot_map[snap.date] = SnapshotData(
            date=snap.date,
            nav=existing.nav + snap.nav,
            renda_fixa=existing.renda_fixa + (snap.renda_fixa or Decimal("0")),
            fundos_investimento=existing.fundos_investimento + (snap.fundos_investimento or Decimal("0")),
            renda_variavel=existing.renda_variavel + (snap.renda_variavel or Decimal("0")),
            derivativos=existing.derivativos + (snap.derivativos or Decimal("0")),
            conta_corrente=existing.conta_corrente + (snap.conta_corrente or Decimal("0")),
            coe=existing.coe + (snap.coe or Decimal("0")),
        )

    return snapshot_map


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


def calculate_stock_market_value(
    positions: dict[UUID, PositionState],
    prices: dict[UUID, Decimal],
) -> Decimal:
    """
    Calculate total market value of stock positions (renda variavel only).

    Returns: total market value of long positions minus short positions
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

    return long_value - short_value


def find_previous_snapshot(
    snapshot_dates: list[date],
    current_date: date,
) -> date | None:
    """Find the most recent snapshot date on or before current_date."""
    result = None
    for snap_date in snapshot_dates:
        if snap_date <= current_date:
            result = snap_date
        else:
            break
    return result


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


def get_cash_flows_between_snapshots(
    cash_flows_by_date: dict[date, list[CashFlow]],
    prev_snap_date: date | None,
    current_snap_date: date,
) -> tuple[Decimal, Decimal]:
    """
    Calculate total deposits and withdrawals between two snapshot dates.

    Returns (total_deposits, total_withdrawals) in BRL.
    """
    total_deposits = Decimal("0")
    total_withdrawals = Decimal("0")

    start_date = prev_snap_date + timedelta(days=1) if prev_snap_date else date(1900, 1, 1)

    for cf_date, flows in cash_flows_by_date.items():
        if start_date <= cf_date <= current_snap_date:
            for cf in flows:
                amount_brl = cf.amount * cf.exchange_rate
                if cf.type == CashFlowType.DEPOSIT:
                    total_deposits += amount_brl
                elif cf.type == CashFlowType.WITHDRAWAL:
                    total_withdrawals += amount_brl

    return total_deposits, total_withdrawals


async def backfill_nav():
    """
    Backfill historical NAV and FundShare records using PortfolioSnapshot as source of truth.

    Key insight: The share_value should only change with market movements, NOT with deposits/withdrawals.

    Formula for TWR (Time-Weighted Return):
    - When deposit occurs: new_shares = deposit / current_share_value
    - NAV increases by deposit amount, shares increase, share_value stays same
    - share_value only changes with market returns

    For snapshots that include deposits:
    - NAV_market = NAV_snapshot - net_deposits_in_period
    - share_value = NAV_market / shares_before_deposits
    - Then issue new shares for deposits at this share_value
    """
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("BACKFILL HISTORICAL NAV (Time-Weighted Return Method)")
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

        # Get portfolio snapshots (source of truth from statements)
        snapshots = await get_portfolio_snapshots(db, user_id)
        snapshot_dates = sorted(snapshots.keys())

        print(f"Found {len(snapshots)} portfolio snapshots (from statements)")
        if snapshot_dates:
            print(f"  First: {snapshot_dates[0]}")
            print(f"  Last: {snapshot_dates[-1]}")
        print()

        if not snapshots:
            print("No portfolio snapshots found.")
            print("Run backfill_portfolio_snapshots.py first.")
            return

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
        prev_snap_date: date | None = None

        # Process each trading day
        fund_shares_created = 0
        cash_flows_updated = 0
        snapshot_used = 0
        interpolated = 0

        print("Processing trading days...")
        print("  Legend: [S] = Snapshot used, [I] = Interpolated")
        print()

        for i, current_date in enumerate(trading_days):
            # Apply all transactions up to and including current_date
            while txn_index < len(transactions):
                txn = transactions[txn_index]
                txn_date = txn.executed_at.date() if isinstance(txn.executed_at, datetime) else txn.executed_at

                if txn_date > current_date:
                    break

                apply_transaction_to_positions(positions, txn)
                txn_index += 1

            # Find the applicable snapshot
            applicable_snap_date = find_previous_snapshot(snapshot_dates, current_date)

            # Calculate NAV for this day
            if current_date in snapshots:
                # This is a snapshot day - use snapshot NAV as source of truth
                snap = snapshots[current_date]
                nav_snapshot = snap.nav
                snapshot_used += 1
                source = "S"

                # Get cash flows that occurred since last snapshot (or from beginning)
                deposits, withdrawals = get_cash_flows_between_snapshots(
                    cash_flows_by_date, prev_snap_date, current_date
                )
                net_cash_flow = deposits - withdrawals

                # Calculate NAV excluding new cash flows (market performance only)
                # NAV_market = NAV_snapshot - net_deposits_in_period
                nav_market = nav_snapshot - net_cash_flow

                # If this is the first snapshot
                if shares_outstanding <= 0:
                    # First snapshot: initialize shares
                    # 1. Create shares from deposits at initial value
                    if deposits > 0:
                        shares_outstanding = deposits / INITIAL_SHARE_VALUE

                    # 2. Redeem shares for withdrawals at initial value
                    if withdrawals > 0 and shares_outstanding > 0:
                        shares_to_redeem = withdrawals / INITIAL_SHARE_VALUE
                        shares_outstanding -= shares_to_redeem

                    # 3. Calculate share_value from remaining shares
                    if shares_outstanding > 0:
                        share_value = nav_snapshot / shares_outstanding
                    else:
                        shares_outstanding = nav_snapshot / INITIAL_SHARE_VALUE
                        share_value = INITIAL_SHARE_VALUE
                else:
                    # Calculate share_value from market NAV (before adding new deposits' shares)
                    share_value = nav_market / shares_outstanding if shares_outstanding > 0 else INITIAL_SHARE_VALUE

                    # Now issue new shares for deposits at this share_value
                    if deposits > 0:
                        new_shares = deposits / share_value
                        shares_outstanding += new_shares

                    # Redeem shares for withdrawals at this share_value
                    if withdrawals > 0:
                        shares_to_redeem = withdrawals / share_value
                        shares_outstanding -= shares_to_redeem

                # Update cash flow records with shares_affected
                for cf_date_iter, flows in cash_flows_by_date.items():
                    if (prev_snap_date is None or cf_date_iter > prev_snap_date) and cf_date_iter <= current_date:
                        for cf in flows:
                            amount_brl = cf.amount * cf.exchange_rate
                            shares_affected = amount_brl / share_value
                            if cf.type == CashFlowType.WITHDRAWAL:
                                shares_affected = -shares_affected
                            await update_cash_flow_shares(db, cf, shares_affected)
                            cash_flows_updated += 1

                # NAV for record is the full snapshot NAV (includes deposits)
                nav = nav_snapshot
                prev_snap_date = current_date

            elif applicable_snap_date:
                # Interpolate between snapshots
                prev_snap = snapshots[applicable_snap_date]

                # Get current market prices for stock positions
                asset_ids = [
                    asset_id for asset_id, pos in positions.items()
                    if pos.quantity > 0
                ]
                prices = await get_asset_prices_at_date(db, asset_ids, current_date)

                # Calculate current stock market value
                current_rv = calculate_stock_market_value(positions, prices)

                # Interpolate NAV: keep fixed parts constant, update only RV
                # NAV = (renda_fixa + fundos + derivativos + conta_corrente + coe) + current_RV
                fixed_portion = (
                    prev_snap.renda_fixa +
                    prev_snap.fundos_investimento +
                    prev_snap.derivativos +
                    prev_snap.conta_corrente +
                    prev_snap.coe
                )
                nav = fixed_portion + current_rv
                interpolated += 1
                source = "I"

                # For interpolated days, share_value changes with market
                if shares_outstanding > 0:
                    share_value = nav / shares_outstanding
                else:
                    share_value = INITIAL_SHARE_VALUE
            else:
                # No snapshot available yet, skip this day
                continue

            # Skip days with zero or negative NAV
            if nav <= 0:
                continue

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

            # Progress indicator (show milestones)
            if (i + 1) % 200 == 0:
                print(f"  Processed {i + 1}/{len(trading_days)} days... "
                      f"(Snapshots: {snapshot_used}, Interpolated: {interpolated})")

        # Commit all changes
        await db.commit()

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Trading days processed: {len(trading_days)}")
        print(f"FundShare records created/updated: {fund_shares_created}")
        print(f"  - From snapshots (source of truth): {snapshot_used}")
        print(f"  - Interpolated (between snapshots): {interpolated}")
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
            if latest.daily_return:
                print(f"  Daily Return: {latest.daily_return * 100:.4f}%")
            if latest.cumulative_return:
                print(f"  Cumulative Return: {latest.cumulative_return * 100:.2f}%")

        # Show first and last snapshots used
        if snapshot_dates:
            first_snap = snapshots[snapshot_dates[0]]
            last_snap = snapshots[snapshot_dates[-1]]
            print("\nSnapshot Summary (Source of Truth):")
            print(f"  First: {first_snap.date} - NAV: R$ {first_snap.nav:,.2f}")
            print(f"  Last:  {last_snap.date} - NAV: R$ {last_snap.nav:,.2f}")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(backfill_nav())
