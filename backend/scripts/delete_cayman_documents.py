#!/usr/bin/env python3
"""
Delete all documents and related data for BTG Cayman account.

This allows re-importing statements with fixed parser.

Usage:
    python -m scripts.delete_cayman_documents --dry-run
    python -m scripts.delete_cayman_documents --confirm
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import Account, Document, Transaction, CashFlow, Position


async def get_cayman_account(db: AsyncSession) -> Account | None:
    """Get BTG Cayman account."""
    query = select(Account).where(Account.name == "BTG Cayman 36595")
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def count_related_data(db: AsyncSession, account_id) -> dict:
    """Count data related to the account."""
    from sqlalchemy import func

    counts = {}

    # Documents
    query = select(func.count(Document.id)).where(Document.account_id == account_id)
    result = await db.execute(query)
    counts["documents"] = result.scalar()

    # Transactions
    query = select(func.count(Transaction.id)).where(Transaction.account_id == account_id)
    result = await db.execute(query)
    counts["transactions"] = result.scalar()

    # Cash flows
    query = select(func.count(CashFlow.id)).where(CashFlow.account_id == account_id)
    result = await db.execute(query)
    counts["cash_flows"] = result.scalar()

    # Positions
    query = select(func.count(Position.id)).where(Position.account_id == account_id)
    result = await db.execute(query)
    counts["positions"] = result.scalar()

    return counts


async def delete_account_data(db: AsyncSession, account_id, confirm: bool = False) -> dict:
    """Delete all data related to the account."""
    deleted = {}

    # Delete in order of dependencies
    # 1. Transactions (references document_id)
    query = delete(Transaction).where(Transaction.account_id == account_id)
    result = await db.execute(query)
    deleted["transactions"] = result.rowcount

    # 2. Cash flows (references account_id)
    query = delete(CashFlow).where(CashFlow.account_id == account_id)
    result = await db.execute(query)
    deleted["cash_flows"] = result.rowcount

    # 3. Positions (references account_id)
    query = delete(Position).where(Position.account_id == account_id)
    result = await db.execute(query)
    deleted["positions"] = result.rowcount

    # 4. Documents (references account_id)
    query = delete(Document).where(Document.account_id == account_id)
    result = await db.execute(query)
    deleted["documents"] = result.rowcount

    if confirm:
        await db.commit()
    else:
        await db.rollback()

    return deleted


async def main():
    parser = argparse.ArgumentParser(description="Delete BTG Cayman documents and related data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete the data (REQUIRED to delete)",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.confirm:
        print("ERROR: You must specify either --dry-run or --confirm")
        print("  --dry-run  : Show what would be deleted")
        print("  --confirm  : Actually delete the data")
        sys.exit(1)

    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 60)
        print("DELETE BTG CAYMAN DATA")
        print("=" * 60)

        # Find account
        account = await get_cayman_account(db)
        if not account:
            print("ERROR: BTG Cayman 36595 account not found")
            sys.exit(1)

        print(f"\nAccount: {account.name}")
        print(f"Account ID: {account.id}")
        print(f"Currency: {account.currency}")

        # Count data
        counts = await count_related_data(db, account.id)
        print(f"\nData to delete:")
        for key, value in counts.items():
            print(f"  - {key}: {value}")

        if args.dry_run:
            print("\n[DRY RUN] No data was deleted.")
            print("\nTo actually delete, run:")
            print("  python -m scripts.delete_cayman_documents --confirm")
        else:
            # Actually delete
            print("\nDeleting data...")
            deleted = await delete_account_data(db, account.id, confirm=True)

            print("\nDeleted:")
            for key, value in deleted.items():
                print(f"  - {key}: {value}")

            print("\nDone! You can now re-import the Cayman statements:")
            print("  railway run python -m scripts.batch_import_direct \\")
            print('    --account "BTG Cayman 36595" \\')
            print("    --parser cayman \\")
            print('    --base-dir "Extratos/BTG Minerals Cayman/36595" \\')
            print("    --continue-on-error")


if __name__ == "__main__":
    asyncio.run(main())
