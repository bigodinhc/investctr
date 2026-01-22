#!/usr/bin/env python3
"""
Migrate positions from the most recent statement for each account.

This script replaces all calculated positions with positions extracted directly
from brokerage statements. The statement is the source of truth.

For each account (BTG Pactual, Alliance, BTG Cayman):
1. Find the most recent parsed document
2. Extract stock_positions from raw_extracted_data
3. Clear existing positions for the account
4. Create new positions from the statement

Usage:
    python -m scripts.migrate_positions_from_statements
    python -m scripts.migrate_positions_from_statements --dry-run
    python -m scripts.migrate_positions_from_statements --account "BTG Pactual"
"""

import argparse
import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session_maker
from app.models import Account, Document, Position, Asset
from app.schemas.enums import ParsingStatus
from app.services.position_reconciliation_service import PositionReconciliationService


def parse_decimal(value: Any) -> Decimal:
    """Safely parse a value to Decimal."""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def get_period_end_date(parsed_data: dict):
    """Extract the period end date from parsed data."""
    period = parsed_data.get("period", {})
    end_date_str = period.get("end_date")

    if end_date_str:
        try:
            return datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    return None


async def get_most_recent_document(
    db: AsyncSession,
    account_id,
) -> Document | None:
    """Get the most recent parsed document for an account."""
    query = (
        select(Document)
        .where(
            and_(
                Document.account_id == account_id,
                Document.parsing_status == ParsingStatus.COMPLETED,
                Document.raw_extracted_data.isnot(None),
            )
        )
        .order_by(Document.created_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


def extract_stock_positions(raw_data: dict, account_currency: str = "BRL") -> list[dict]:
    """
    Extract stock positions from raw parsed data.

    Handles different formats from BTG Brasil and BTG Cayman.
    """
    positions = []

    # Try different keys where stock positions might be stored
    stock_positions = raw_data.get("stock_positions", [])

    if not stock_positions:
        # Try alternative key names
        stock_positions = raw_data.get("positions", [])

    if not stock_positions:
        # Cayman format might have different structure
        stock_positions = raw_data.get("equities", [])

    for pos in stock_positions:
        if not pos:
            continue

        ticker = pos.get("ticker", "").upper().strip()
        if not ticker:
            continue

        # Parse quantity
        quantity = parse_decimal(pos.get("quantity", 0))
        if quantity == Decimal("0"):
            continue

        # Parse average price
        avg_price = parse_decimal(
            pos.get("avg_price")
            or pos.get("average_price")
            or pos.get("preco_medio")
            or pos.get("cost_basis")
            or 0
        )

        # Parse current price (optional)
        current_price = parse_decimal(
            pos.get("current_price")
            or pos.get("preco_atual")
            or pos.get("last_price")
            or 0
        )

        # Parse total cost
        total_cost = parse_decimal(
            pos.get("total_cost")
            or pos.get("total")
            or pos.get("custo_total")
            or 0
        )
        if total_cost == Decimal("0") and avg_price > 0:
            total_cost = abs(quantity) * avg_price

        positions.append({
            "ticker": ticker,
            "quantity": quantity,
            "avg_price": avg_price,
            "total_cost": total_cost,
            "current_price": current_price if current_price > 0 else None,
        })

    return positions


async def migrate_positions_for_account(
    db: AsyncSession,
    account: Account,
    dry_run: bool = False,
) -> dict:
    """
    Migrate positions for a single account from its most recent statement.

    Returns dict with results.
    """
    result = {
        "account_name": account.name,
        "account_id": str(account.id),
        "document": None,
        "period_end": None,
        "positions_found": 0,
        "positions_created": 0,
        "errors": [],
    }

    # Get most recent document
    document = await get_most_recent_document(db, account.id)
    if not document:
        result["errors"].append("No parsed document found")
        return result

    result["document"] = document.file_name

    # Get period end date
    raw_data = document.raw_extracted_data
    period_end = get_period_end_date(raw_data)
    result["period_end"] = str(period_end) if period_end else "unknown"

    # Extract stock positions
    stock_positions = extract_stock_positions(raw_data, account.currency)
    result["positions_found"] = len(stock_positions)

    if not stock_positions:
        result["errors"].append("No stock positions found in document")
        return result

    print(f"\n  Found {len(stock_positions)} stock positions:")
    for pos in stock_positions[:10]:
        qty_str = f"{pos['quantity']:,.0f}" if pos['quantity'] == int(pos['quantity']) else f"{pos['quantity']:,.2f}"
        print(f"    {pos['ticker']:<10} Qty: {qty_str:>12}  Avg: {pos['avg_price']:>12,.2f}")
    if len(stock_positions) > 10:
        print(f"    ... and {len(stock_positions) - 10} more")

    if dry_run:
        print("\n  [DRY RUN] Would migrate these positions")
        return result

    # Use reconciliation service to migrate
    service = PositionReconciliationService(db)
    migration_result = await service.migrate_positions_from_statement(
        account_id=account.id,
        document_id=document.id,
        statement_positions=stock_positions,
    )

    result["positions_created"] = migration_result.positions_created
    result["errors"].extend(migration_result.errors)

    return result


async def migrate_all_positions(
    account_filter: str | None = None,
    dry_run: bool = False,
):
    """Migrate positions for all accounts from their most recent statements."""
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("MIGRATE POSITIONS FROM STATEMENTS")
        print("=" * 70)
        if dry_run:
            print("[DRY RUN MODE - No changes will be made]")
        print()

        # Get all accounts
        query = select(Account).where(Account.is_active == True)
        if account_filter:
            query = query.where(Account.name.ilike(f"%{account_filter}%"))
        query = query.order_by(Account.name)

        result = await db.execute(query)
        accounts = list(result.scalars().all())

        print(f"Found {len(accounts)} accounts to process")

        results = []
        for account in accounts:
            print(f"\n{'='*50}")
            print(f"Account: {account.name} ({account.currency})")
            print(f"{'='*50}")

            try:
                account_result = await migrate_positions_for_account(
                    db=db,
                    account=account,
                    dry_run=dry_run,
                )
                results.append(account_result)
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                results.append({
                    "account_name": account.name,
                    "account_id": str(account.id),
                    "errors": [str(e)],
                })

        if not dry_run:
            await db.commit()

        # Print summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)

        total_created = 0
        total_errors = 0

        for r in results:
            status = "✓" if r.get("positions_created", 0) > 0 else "✗" if r.get("errors") else "-"
            created = r.get("positions_created", 0)
            found = r.get("positions_found", 0)
            errors = len(r.get("errors", []))
            total_created += created
            total_errors += errors

            print(f"{status} {r['account_name']:<25} Found: {found:>3}  Created: {created:>3}  Errors: {errors}")

        print(f"\nTotal positions created: {total_created}")
        print(f"Total errors: {total_errors}")

        # Verify positions in database
        if not dry_run:
            count_query = (
                select(func.count())
                .select_from(Position)
                .where(Position.source == "statement")
            )
            count_result = await db.execute(count_query)
            statement_positions = count_result.scalar()

            print(f"\nPositions with source='statement' in database: {statement_positions}")

            # Show sample positions
            sample_query = (
                select(Position)
                .options(selectinload(Position.asset))
                .where(Position.source == "statement")
                .order_by(Position.updated_at.desc())
                .limit(10)
            )
            sample_result = await db.execute(sample_query)
            sample_positions = list(sample_result.scalars().all())

            if sample_positions:
                print("\nSample positions (most recently updated):")
                print("-" * 80)
                print(f"{'Ticker':<10} {'Quantity':>15} {'Avg Price':>15} {'Total Cost':>15}")
                print("-" * 80)
                for pos in sample_positions:
                    ticker = pos.asset.ticker if pos.asset else "unknown"
                    qty_str = f"{pos.quantity:,.0f}" if pos.quantity == int(pos.quantity) else f"{pos.quantity:,.2f}"
                    print(f"{ticker:<10} {qty_str:>15} {pos.avg_price:>15,.2f} {pos.total_cost:>15,.2f}")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("1. Run NAV calculation: python -m scripts.consolidate_portfolio")
        print("2. Verify positions in dashboard")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Migrate positions from statements to database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--account",
        type=str,
        help="Filter to specific account name (partial match)",
    )
    args = parser.parse_args()

    asyncio.run(migrate_all_positions(
        account_filter=args.account,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
