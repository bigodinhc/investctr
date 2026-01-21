#!/usr/bin/env python3
"""
Backfill PortfolioSnapshots from document consolidated_position data.

This script extracts the consolidated_position from all imported documents
and creates PortfolioSnapshot records with the official values from BTG statements.

The consolidated_position in BTG statements contains the official breakdown:
- renda_fixa: Fixed income total
- fundos_investimento: Investment funds total
- renda_variavel: Variable income (stocks) total
- derivativos: Derivatives total
- conta_corrente: Checking account balance
- coe: COE total
- total: Total portfolio value (NAV)

This value is the SOURCE OF TRUTH as it's calculated by BTG, not by us.

Usage:
    python -m scripts.backfill_portfolio_snapshots

Or from backend directory:
    python scripts/backfill_portfolio_snapshots.py
"""

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

from app.database import get_session_maker
from app.models import Account, Document, PortfolioSnapshot
from app.schemas.enums import ParsingStatus


def parse_decimal(value: Any) -> Decimal:
    """Safely parse a value to Decimal."""
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def get_period_end_date(parsed_data: dict) -> datetime | None:
    """Extract the period end date from parsed data."""
    period = parsed_data.get("period", {})
    end_date_str = period.get("end_date")

    if end_date_str:
        try:
            return datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except Exception:
            pass

    return None


async def backfill_portfolio_snapshots():
    """Backfill PortfolioSnapshot records from document data."""
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("BACKFILL PORTFOLIO SNAPSHOTS")
        print("=" * 70)
        print("Extracting consolidated_position from imported documents")
        print()

        # Query all documents with parsed data
        query = (
            select(Document)
            .join(Account, Document.account_id == Account.id)
            .where(Document.parsing_status == ParsingStatus.COMPLETED)
            .where(Document.raw_extracted_data.isnot(None))
            .order_by(Document.created_at.asc())
        )
        result = await db.execute(query)
        documents = list(result.scalars().all())

        print(f"Found {len(documents)} parsed documents")
        print()

        if not documents:
            print("No documents to process.")
            return

        # Get account info for user_id lookup
        account_query = select(Account)
        account_result = await db.execute(account_query)
        accounts = {acc.id: acc for acc in account_result.scalars().all()}

        snapshots_created = 0
        snapshots_updated = 0
        errors = []

        for doc in documents:
            try:
                parsed_data = doc.raw_extracted_data
                if not parsed_data:
                    continue

                # Get period end date
                end_date = get_period_end_date(parsed_data)
                if not end_date:
                    errors.append(f"{doc.file_name}: No period end date found")
                    continue

                # Get consolidated_position
                consolidated = parsed_data.get("consolidated_position", {})

                # Handle both new format (with total) and potential variations
                nav = parse_decimal(consolidated.get("total", 0))

                # If no consolidated_position or total is 0, try to calculate from components
                if nav == 0:
                    # Sum up components
                    nav = (
                        parse_decimal(consolidated.get("renda_fixa", 0)) +
                        parse_decimal(consolidated.get("fundos_investimento", 0)) +
                        parse_decimal(consolidated.get("renda_variavel", 0)) +
                        parse_decimal(consolidated.get("derivativos", 0)) +
                        parse_decimal(consolidated.get("conta_corrente", 0)) +
                        parse_decimal(consolidated.get("coe", 0))
                    )

                if nav == 0:
                    errors.append(f"{doc.file_name}: No NAV found in consolidated_position")
                    continue

                # Get account and user_id
                account = accounts.get(doc.account_id)
                if not account:
                    errors.append(f"{doc.file_name}: Account not found")
                    continue

                user_id = account.user_id

                # Check if snapshot already exists
                existing_query = select(PortfolioSnapshot).where(
                    and_(
                        PortfolioSnapshot.user_id == user_id,
                        PortfolioSnapshot.date == end_date,
                        PortfolioSnapshot.account_id == account.id,
                    )
                )
                existing_result = await db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()

                # Get currency from account
                currency = account.currency or "BRL"
                currency_symbol = "$" if currency == "USD" else "R$"

                # Handle both BTG Brasil and BTG Cayman formats
                # BTG Brasil: renda_fixa, fundos_investimento, renda_variavel, derivativos, conta_corrente, coe
                # BTG Cayman: cash, equities_long, equities_short, derivatives, structured_products
                renda_fixa = parse_decimal(consolidated.get("renda_fixa", 0))
                fundos = parse_decimal(consolidated.get("fundos_investimento", 0))
                renda_variavel = parse_decimal(consolidated.get("renda_variavel", 0))
                derivativos = parse_decimal(consolidated.get("derivativos", 0))
                conta_corrente = parse_decimal(consolidated.get("conta_corrente", 0))
                coe = parse_decimal(consolidated.get("coe", 0))

                # Map Cayman fields to Brasil fields if needed
                if currency == "USD":
                    # Cayman format
                    cash = parse_decimal(consolidated.get("cash", 0))
                    equities_long = parse_decimal(consolidated.get("equities_long", 0))
                    equities_short = parse_decimal(consolidated.get("equities_short", 0))
                    derivatives = parse_decimal(consolidated.get("derivatives", 0))
                    structured = parse_decimal(consolidated.get("structured_products", 0))

                    # Map to standard fields
                    conta_corrente = cash
                    renda_variavel = equities_long + equities_short  # short is negative
                    derivativos = derivatives
                    renda_fixa = structured  # structured products are like fixed income

                if existing:
                    # Update existing snapshot
                    existing.nav = nav
                    existing.currency = currency
                    existing.renda_fixa = renda_fixa
                    existing.fundos_investimento = fundos
                    existing.renda_variavel = renda_variavel
                    existing.derivativos = derivativos
                    existing.conta_corrente = conta_corrente
                    existing.coe = coe
                    existing.document_id = doc.id
                    snapshots_updated += 1
                    print(f"  Updated: {end_date} - NAV: {currency_symbol} {nav:,.2f} ({currency})")
                else:
                    # Create new snapshot
                    snapshot = PortfolioSnapshot(
                        user_id=user_id,
                        account_id=account.id,
                        date=end_date,
                        document_id=doc.id,
                        nav=nav,
                        currency=currency,
                        total_cost=nav,  # Use NAV as cost since we don't track cost separately
                        realized_pnl=Decimal("0"),
                        unrealized_pnl=Decimal("0"),
                        renda_fixa=renda_fixa,
                        fundos_investimento=fundos,
                        renda_variavel=renda_variavel,
                        derivativos=derivativos,
                        conta_corrente=conta_corrente,
                        coe=coe,
                    )
                    db.add(snapshot)
                    snapshots_created += 1
                    print(f"  Created: {end_date} - NAV: {currency_symbol} {nav:,.2f} ({currency})")

            except Exception as e:
                errors.append(f"{doc.file_name}: {str(e)}")

        # Commit all changes
        await db.commit()

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Snapshots created: {snapshots_created}")
        print(f"Snapshots updated: {snapshots_updated}")
        print(f"Errors: {len(errors)}")

        if errors:
            print("\nErrors:")
            for error in errors[:10]:
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")

        # Verify snapshots
        count_query = select(func.count()).select_from(PortfolioSnapshot)
        count_result = await db.execute(count_query)
        total_snapshots = count_result.scalar()

        print(f"\nTotal PortfolioSnapshot records in database: {total_snapshots}")

        # Show latest snapshots
        latest_query = (
            select(PortfolioSnapshot)
            .order_by(PortfolioSnapshot.date.desc())
            .limit(5)
        )
        latest_result = await db.execute(latest_query)
        latest_snapshots = list(latest_result.scalars().all())

        if latest_snapshots:
            print("\nLatest snapshots:")
            print("-" * 80)
            print(f"{'Date':<12} {'Currency':<6} {'NAV':>18} {'Cash/RF':>15} {'RV':>15}")
            print("-" * 80)
            for snap in latest_snapshots:
                currency = getattr(snap, 'currency', 'BRL') or 'BRL'
                symbol = "$" if currency == "USD" else "R$"
                nav_str = f"{symbol} {snap.nav:,.2f}" if snap.nav else "N/A"
                rf_str = f"{snap.renda_fixa or snap.conta_corrente or 0:,.2f}" if (snap.renda_fixa or snap.conta_corrente) else "-"
                rv_str = f"{snap.renda_variavel or 0:,.2f}" if snap.renda_variavel else "-"
                print(f"{snap.date!s:<12} {currency:<6} {nav_str:>18} {rf_str:>15} {rv_str:>15}")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("1. Run NAV backfill: python -m scripts.backfill_nav")
        print("   This will recalculate FundShare records using snapshot NAV values")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(backfill_portfolio_snapshots())
