#!/usr/bin/env python3
"""
Backfill missing cash flows from documents.

This script extracts transfer_in and transfer_out movements from documents'
raw_extracted_data and inserts them into the cash_flows table.

The problem: cash_flows table only has R$ 3M deposits, but documents show R$ 19.6M.
This causes backfill_nav.py to incorrectly calculate TWR (shows 543% instead of ~123%).

Usage:
    python -m scripts.backfill_cash_flows
"""

import asyncio
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import Account, CashFlow, Document
from app.schemas.enums import CashFlowType


async def get_user_and_account(db: AsyncSession) -> tuple[UUID, UUID] | None:
    """Get the single user ID and account ID (assumes single-user system)."""
    query = select(Account).limit(1)
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        return None

    return account.user_id, account.id


async def get_existing_cash_flows(
    db: AsyncSession, account_id: UUID
) -> set[tuple[str, str, float]]:
    """
    Get existing cash flows as a set of (date, type, amount) tuples for deduplication.
    """
    query = select(CashFlow).where(CashFlow.account_id == account_id)
    result = await db.execute(query)
    cash_flows = result.scalars().all()

    existing = set()
    for cf in cash_flows:
        cf_date = cf.executed_at.date() if isinstance(cf.executed_at, datetime) else cf.executed_at
        amount = float(cf.amount * cf.exchange_rate)
        existing.add((str(cf_date), cf.type.value, round(amount, 2)))

    return existing


async def extract_cash_flows_from_documents(
    db: AsyncSession, account_id: UUID
) -> list[dict]:
    """
    Extract transfer_in and transfer_out movements from all documents.
    """
    query = select(Document).where(
        and_(
            Document.account_id == account_id,
            Document.raw_extracted_data.isnot(None),
        )
    )
    result = await db.execute(query)
    documents = result.scalars().all()

    movements = []

    for doc in documents:
        raw_data = doc.raw_extracted_data
        if not raw_data:
            continue

        cash_movements = raw_data.get("cash_movements", {})
        if not cash_movements:
            continue

        mvmts = cash_movements.get("movements", [])
        if not mvmts:
            continue

        for m in mvmts:
            m_type = m.get("type")
            if m_type not in ("transfer_in", "transfer_out"):
                continue

            m_date = m.get("date")
            m_value = m.get("value")
            m_desc = m.get("description", "")

            if not m_date or m_value is None:
                continue

            # Map type
            if m_type == "transfer_in":
                cf_type = CashFlowType.DEPOSIT
                amount = abs(float(m_value))
            else:  # transfer_out
                cf_type = CashFlowType.WITHDRAWAL
                amount = abs(float(m_value))

            movements.append({
                "date": m_date,
                "type": cf_type,
                "amount": amount,
                "description": m_desc,
                "document_id": str(doc.id),
                "file_name": doc.file_name,
            })

    return movements


async def backfill_cash_flows():
    """
    Main function to backfill cash flows from documents.
    """
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("BACKFILL CASH FLOWS FROM DOCUMENTS")
        print("=" * 70)
        print()

        # Get user and account
        result = await get_user_and_account(db)
        if not result:
            print("No accounts found. Cannot backfill cash flows.")
            return

        user_id, account_id = result
        print(f"User ID: {user_id}")
        print(f"Account ID: {account_id}")
        print()

        # Get existing cash flows for deduplication
        existing = await get_existing_cash_flows(db, account_id)
        print(f"Existing cash flows in database: {len(existing)}")

        # Extract cash flows from documents
        doc_movements = await extract_cash_flows_from_documents(db, account_id)
        print(f"Cash flows found in documents: {len(doc_movements)}")
        print()

        # Filter out duplicates
        new_movements = []
        duplicates = 0

        for m in doc_movements:
            key = (m["date"], m["type"].value, round(m["amount"], 2))
            if key in existing:
                duplicates += 1
            else:
                new_movements.append(m)
                existing.add(key)  # Prevent duplicates within this batch

        print(f"Duplicates (already in DB): {duplicates}")
        print(f"New cash flows to insert: {len(new_movements)}")
        print()

        if not new_movements:
            print("No new cash flows to insert.")
            return

        # Display what we're going to insert
        print("NEW CASH FLOWS TO INSERT:")
        print("-" * 70)

        total_deposits = Decimal("0")
        total_withdrawals = Decimal("0")

        for m in sorted(new_movements, key=lambda x: x["date"]):
            amount = Decimal(str(m["amount"]))
            type_str = "DEPOSIT" if m["type"] == CashFlowType.DEPOSIT else "WITHDRAWAL"

            if m["type"] == CashFlowType.DEPOSIT:
                total_deposits += amount
            else:
                total_withdrawals += amount

            print(f"  {m['date']} | {type_str:12} | R$ {float(amount):>15,.2f} | {m['description'][:40]}")

        print("-" * 70)
        print(f"Total new deposits:    R$ {float(total_deposits):>15,.2f}")
        print(f"Total new withdrawals: R$ {float(total_withdrawals):>15,.2f}")
        print(f"Net new cash flow:     R$ {float(total_deposits - total_withdrawals):>15,.2f}")
        print()

        # Insert new cash flows
        print("Inserting cash flows...")

        inserted = 0
        for m in new_movements:
            # Parse date
            if isinstance(m["date"], str):
                m_date = datetime.strptime(m["date"], "%Y-%m-%d")
            else:
                m_date = m["date"]

            cash_flow = CashFlow(
                account_id=account_id,
                type=m["type"],
                amount=Decimal(str(m["amount"])),
                currency="BRL",
                exchange_rate=Decimal("1.0"),
                executed_at=m_date,
                notes=m["description"],
            )
            db.add(cash_flow)
            inserted += 1

        await db.commit()

        print(f"Inserted {inserted} new cash flows.")
        print()

        # Verify totals
        print("=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        # Query totals
        from sqlalchemy import func

        deposit_query = select(func.sum(CashFlow.amount * CashFlow.exchange_rate)).where(
            and_(
                CashFlow.account_id == account_id,
                CashFlow.type == CashFlowType.DEPOSIT,
            )
        )
        withdrawal_query = select(func.sum(CashFlow.amount * CashFlow.exchange_rate)).where(
            and_(
                CashFlow.account_id == account_id,
                CashFlow.type == CashFlowType.WITHDRAWAL,
            )
        )

        total_deps = (await db.execute(deposit_query)).scalar() or Decimal("0")
        total_wdrs = (await db.execute(withdrawal_query)).scalar() or Decimal("0")

        print(f"Total deposits in DB:    R$ {float(total_deps):>15,.2f}")
        print(f"Total withdrawals in DB: R$ {float(total_wdrs):>15,.2f}")
        print(f"Net cash flow in DB:     R$ {float(total_deps - total_wdrs):>15,.2f}")
        print()
        print("=" * 70)
        print("NEXT STEP: Run backfill_nav.py to recalculate TWR with complete cash flows")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(backfill_cash_flows())
