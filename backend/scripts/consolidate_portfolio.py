#!/usr/bin/env python3
"""
Consolidate portfolio snapshots across multiple accounts.

This script creates consolidated NAV records that sum:
- NAV from all BRL accounts directly
- NAV from USD accounts converted to BRL using PTAX rate

It also calculates consolidated TWR (Time-Weighted Return) where internal
transfers between accounts automatically cancel out.

Usage:
    python -m scripts.consolidate_portfolio
    python -m scripts.consolidate_portfolio --exchange-rate 6.0
    python -m scripts.consolidate_portfolio --from-date 2022-11-01
"""

import argparse
import asyncio
import sys
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import Account, PortfolioSnapshot, CashFlow
from app.schemas.enums import CashFlowType


# Default exchange rate USD/BRL (can be overridden)
DEFAULT_EXCHANGE_RATE = Decimal("6.0")


async def get_user_id(db: AsyncSession) -> str:
    """Get user_id from existing accounts."""
    query = select(Account.user_id).limit(1)
    result = await db.execute(query)
    user_id = result.scalar_one_or_none()
    if not user_id:
        raise ValueError("No accounts found in database")
    return user_id


async def get_all_accounts(db: AsyncSession) -> list[Account]:
    """Get all active accounts."""
    query = select(Account).where(Account.is_active == True).order_by(Account.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_portfolio_snapshots_by_date(
    db: AsyncSession,
) -> dict[date, list[PortfolioSnapshot]]:
    """Get all portfolio snapshots grouped by date."""
    query = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.account_id.isnot(None))
        .order_by(PortfolioSnapshot.date, PortfolioSnapshot.account_id)
    )
    result = await db.execute(query)
    snapshots = result.scalars().all()

    # Group by date
    by_date = defaultdict(list)
    for snapshot in snapshots:
        by_date[snapshot.date].append(snapshot)

    return dict(by_date)


async def get_cash_flows(db: AsyncSession) -> list[CashFlow]:
    """Get all cash flows (deposits and withdrawals only)."""
    query = (
        select(CashFlow)
        .where(
            CashFlow.type.in_([CashFlowType.DEPOSIT, CashFlowType.WITHDRAWAL])
        )
        .order_by(CashFlow.executed_at)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


def get_exchange_rate(snapshot_date: date, default_rate: Decimal) -> Decimal:
    """
    Get USD/BRL exchange rate for a given date.

    For now, uses a fixed rate. In production, this should fetch PTAX rates
    from BCB API or stored historical rates.
    """
    # TODO: Implement PTAX rate fetching from BCB API
    # https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia
    return default_rate


def calculate_consolidated_nav(
    snapshots: list[PortfolioSnapshot],
    exchange_rate: Decimal,
) -> dict:
    """
    Calculate consolidated NAV from multiple account snapshots.

    Returns:
        dict with nav_brl, nav_usd, nav_total_brl, breakdown by account
    """
    nav_brl = Decimal("0")
    nav_usd = Decimal("0")
    breakdown = []

    for snapshot in snapshots:
        currency = getattr(snapshot, "currency", "BRL")
        nav = snapshot.nav

        if currency == "USD":
            nav_usd += nav
        else:
            nav_brl += nav

        breakdown.append({
            "account_id": str(snapshot.account_id),
            "nav": float(nav),
            "currency": currency,
        })

    # Convert USD to BRL
    nav_usd_in_brl = nav_usd * exchange_rate
    nav_total_brl = nav_brl + nav_usd_in_brl

    return {
        "nav_brl": nav_brl,
        "nav_usd": nav_usd,
        "nav_usd_in_brl": nav_usd_in_brl,
        "nav_total_brl": nav_total_brl,
        "exchange_rate": exchange_rate,
        "breakdown": breakdown,
    }


def calculate_consolidated_cash_flows(
    cash_flows: list[CashFlow],
    exchange_rate: Decimal,
) -> dict:
    """
    Calculate consolidated cash flows across all accounts.

    Internal transfers between accounts of the same user will
    cancel out (deposit in one account = withdrawal in another).

    Returns:
        dict with total_deposits_brl, total_withdrawals_brl, net_flow_brl
    """
    total_deposits_brl = Decimal("0")
    total_withdrawals_brl = Decimal("0")

    for cf in cash_flows:
        # Convert to BRL if needed
        currency = cf.currency
        amount = cf.amount
        rate = exchange_rate if currency == "USD" else Decimal("1")
        amount_brl = amount * rate

        if cf.type == CashFlowType.DEPOSIT:
            total_deposits_brl += abs(amount_brl)
        elif cf.type == CashFlowType.WITHDRAWAL:
            total_withdrawals_brl += abs(amount_brl)

    net_flow_brl = total_deposits_brl - total_withdrawals_brl

    return {
        "total_deposits_brl": total_deposits_brl,
        "total_withdrawals_brl": total_withdrawals_brl,
        "net_flow_brl": net_flow_brl,
    }


def calculate_twr(
    nav_series: list[tuple[date, Decimal]],
    cash_flow_series: list[tuple[date, Decimal]],
) -> Decimal:
    """
    Calculate Time-Weighted Return (TWR).

    TWR = (1 + r1) * (1 + r2) * ... * (1 + rn) - 1

    Where ri is the sub-period return between cash flows.
    """
    if len(nav_series) < 2:
        return Decimal("0")

    # Sort both series by date
    nav_series = sorted(nav_series, key=lambda x: x[0])
    cash_flow_dict = {}
    for cf_date, cf_amount in cash_flow_series:
        if cf_date in cash_flow_dict:
            cash_flow_dict[cf_date] += cf_amount
        else:
            cash_flow_dict[cf_date] = cf_amount

    # Calculate sub-period returns
    compound_return = Decimal("1")

    for i in range(1, len(nav_series)):
        prev_date, prev_nav = nav_series[i - 1]
        curr_date, curr_nav = nav_series[i]

        # Get cash flow at beginning of this period (if any)
        cf_amount = cash_flow_dict.get(curr_date, Decimal("0"))

        # Adjusted previous NAV = prev_nav + cash_flow
        adjusted_prev_nav = prev_nav + cf_amount

        if adjusted_prev_nav > 0:
            period_return = curr_nav / adjusted_prev_nav
            compound_return *= period_return

    twr = compound_return - Decimal("1")
    return twr


async def create_consolidated_snapshot(
    db: AsyncSession,
    user_id: str,
    snapshot_date: date,
    nav_data: dict,
) -> PortfolioSnapshot:
    """Create or update a consolidated portfolio snapshot (account_id = NULL)."""
    # Check for existing consolidated snapshot
    query = select(PortfolioSnapshot).where(
        and_(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.date == snapshot_date,
            PortfolioSnapshot.account_id.is_(None),
        )
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        existing.nav = nav_data["nav_total_brl"]
        existing.currency = "BRL"
        return existing
    else:
        # Create new
        snapshot = PortfolioSnapshot(
            user_id=user_id,
            date=snapshot_date,
            account_id=None,  # Consolidated snapshot
            nav=nav_data["nav_total_brl"],
            currency="BRL",
            total_cost=Decimal("0"),  # Not tracked for consolidated
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
        )
        db.add(snapshot)
        return snapshot


async def main():
    parser = argparse.ArgumentParser(description="Consolidate portfolio across accounts")
    parser.add_argument(
        "--exchange-rate",
        type=float,
        default=float(DEFAULT_EXCHANGE_RATE),
        help=f"USD/BRL exchange rate (default: {DEFAULT_EXCHANGE_RATE})",
    )
    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date (YYYY-MM-DD) for consolidation",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show consolidation without saving",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed breakdown for each date",
    )
    args = parser.parse_args()

    exchange_rate = Decimal(str(args.exchange_rate))
    from_date = datetime.strptime(args.from_date, "%Y-%m-%d").date() if args.from_date else None

    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("PORTFOLIO CONSOLIDATION")
        print("=" * 70)

        # Get accounts
        accounts = await get_all_accounts(db)
        print(f"\nAccounts found: {len(accounts)}")
        for account in accounts:
            print(f"  - {account.name} ({account.currency})")

        # Get user_id
        user_id = await get_user_id(db)
        print(f"\nUser ID: {user_id}")
        print(f"Exchange rate (USD/BRL): {exchange_rate}")

        # Get snapshots by date
        snapshots_by_date = await get_portfolio_snapshots_by_date(db)
        print(f"\nDates with snapshots: {len(snapshots_by_date)}")

        if from_date:
            snapshots_by_date = {
                d: s for d, s in snapshots_by_date.items() if d >= from_date
            }
            print(f"After filtering from {from_date}: {len(snapshots_by_date)}")

        # Get all cash flows
        cash_flows = await get_cash_flows(db)
        print(f"Total cash flows (deposits/withdrawals): {len(cash_flows)}")

        # Calculate consolidated values for each date
        print("\n" + "-" * 70)
        print("CONSOLIDATION BY DATE")
        print("-" * 70)

        nav_series = []
        consolidated_created = 0

        for snapshot_date in sorted(snapshots_by_date.keys()):
            snapshots = snapshots_by_date[snapshot_date]

            # Calculate consolidated NAV
            rate = get_exchange_rate(snapshot_date, exchange_rate)
            nav_data = calculate_consolidated_nav(snapshots, rate)

            nav_series.append((snapshot_date, nav_data["nav_total_brl"]))

            if args.verbose:
                print(f"\n{snapshot_date}:")
                print(f"  NAV BRL: R$ {nav_data['nav_brl']:,.2f}")
                print(f"  NAV USD: $ {nav_data['nav_usd']:,.2f}")
                print(f"  NAV USD→BRL: R$ {nav_data['nav_usd_in_brl']:,.2f}")
                print(f"  TOTAL: R$ {nav_data['nav_total_brl']:,.2f}")
            else:
                print(f"  {snapshot_date}: R$ {nav_data['nav_total_brl']:,.2f} "
                      f"({len(snapshots)} accounts)")

            # Create consolidated snapshot
            if not args.dry_run:
                await create_consolidated_snapshot(db, user_id, snapshot_date, nav_data)
                consolidated_created += 1

        # Calculate consolidated cash flows
        print("\n" + "-" * 70)
        print("CONSOLIDATED CASH FLOWS")
        print("-" * 70)

        cf_data = calculate_consolidated_cash_flows(cash_flows, exchange_rate)
        print(f"  Total Deposits: R$ {cf_data['total_deposits_brl']:,.2f}")
        print(f"  Total Withdrawals: R$ {cf_data['total_withdrawals_brl']:,.2f}")
        print(f"  Net Flow: R$ {cf_data['net_flow_brl']:,.2f}")

        # Calculate TWR
        if len(nav_series) >= 2:
            print("\n" + "-" * 70)
            print("TIME-WEIGHTED RETURN (TWR)")
            print("-" * 70)

            # Build cash flow series for TWR calculation
            cf_series = []
            for cf in cash_flows:
                rate = exchange_rate if cf.currency == "USD" else Decimal("1")
                amount_brl = cf.amount * rate
                # Deposits are positive inflows, withdrawals are negative
                if cf.type == CashFlowType.WITHDRAWAL:
                    amount_brl = -abs(amount_brl)
                else:
                    amount_brl = abs(amount_brl)
                cf_series.append((cf.executed_at.date(), amount_brl))

            twr = calculate_twr(nav_series, cf_series)
            twr_pct = twr * Decimal("100")

            first_nav = nav_series[0][1]
            last_nav = nav_series[-1][1]

            print(f"  First NAV ({nav_series[0][0]}): R$ {first_nav:,.2f}")
            print(f"  Last NAV ({nav_series[-1][0]}): R$ {last_nav:,.2f}")
            print(f"  TWR: {twr_pct:,.2f}%")

            # Simple return for comparison
            simple_return = (last_nav - first_nav - cf_data['net_flow_brl']) / first_nav * 100
            print(f"  Simple return (for comparison): {simple_return:,.2f}%")

        # Commit if not dry run
        if not args.dry_run:
            await db.commit()
            print(f"\n{consolidated_created} consolidated snapshots created/updated.")
        else:
            print("\n[DRY RUN] No changes were made.")

        print("\n" + "=" * 70)
        print("VERIFICATION QUERIES")
        print("=" * 70)
        print("""
-- 1. NAV per account (latest date)
SELECT
    a.name as conta,
    ps.date,
    ps.nav,
    ps.currency
FROM portfolio_snapshots ps
JOIN accounts a ON ps.account_id = a.id
WHERE ps.date = (SELECT MAX(date) FROM portfolio_snapshots)
ORDER BY a.name;

-- 2. Consolidated NAV by date
SELECT
    date,
    nav as nav_consolidado_brl
FROM portfolio_snapshots
WHERE account_id IS NULL
ORDER BY date DESC
LIMIT 10;

-- 3. Cash flows totals (all accounts)
SELECT
    SUM(CASE WHEN type = 'deposit' THEN amount * exchange_rate ELSE 0 END) as total_deposits,
    SUM(CASE WHEN type = 'withdrawal' THEN amount * exchange_rate ELSE 0 END) as total_withdrawals
FROM cash_flows;
""")


if __name__ == "__main__":
    asyncio.run(main())
