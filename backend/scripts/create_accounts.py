#!/usr/bin/env python3
"""
Create additional accounts for multi-account portfolio support.

This script creates the Alliance Investments and BTG Cayman accounts
for the "Minerals BTG" group consolidation.

Usage:
    python -m scripts.create_accounts
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import Account
from app.schemas.enums import AccountType


# Accounts to create for the Minerals BTG group
ACCOUNTS_TO_CREATE = [
    {
        "name": "Alliance Investments",
        "type": AccountType.BTG_BR,
        "currency": "BRL",
    },
    {
        "name": "BTG Cayman 36595",
        "type": AccountType.BTG_CAYMAN,
        "currency": "USD",
    },
]


async def get_user_id(db: AsyncSession) -> UUID:
    """Get the user ID from an existing account (BTG Pactual)."""
    query = select(Account).where(Account.name == "BTG Pactual")
    result = await db.execute(query)
    account = result.scalar_one_or_none()

    if not account:
        raise ValueError(
            "BTG Pactual account not found. "
            "Please create the primary account first."
        )

    return account.user_id


async def check_account_exists(db: AsyncSession, name: str) -> bool:
    """Check if an account with the given name already exists."""
    query = select(Account).where(Account.name == name)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def create_account(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    account_type: AccountType,
    currency: str,
) -> Account:
    """Create a new account."""
    account = Account(
        user_id=user_id,
        name=name,
        type=account_type,
        currency=currency,
        is_active=True,
    )
    db.add(account)
    await db.flush()
    return account


async def list_accounts(db: AsyncSession) -> list[Account]:
    """List all accounts."""
    query = select(Account).order_by(Account.name)
    result = await db.execute(query)
    return list(result.scalars().all())


async def main():
    parser = argparse.ArgumentParser(description="Create additional accounts")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing accounts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating",
    )
    args = parser.parse_args()

    session_maker = get_session_maker()

    async with session_maker() as db:
        if args.list:
            print("\n=== Existing Accounts ===\n")
            accounts = await list_accounts(db)
            for account in accounts:
                print(
                    f"  - {account.name} ({account.type.value}) "
                    f"[{account.currency}] - ID: {account.id}"
                )
            print()
            return

        print("=" * 60)
        print("CREATE ACCOUNTS FOR MULTI-ACCOUNT PORTFOLIO")
        print("=" * 60)

        # Get user ID from existing account
        user_id = await get_user_id(db)
        print(f"\nUser ID: {user_id}")

        # Process each account
        created = []
        skipped = []

        for account_config in ACCOUNTS_TO_CREATE:
            name = account_config["name"]
            account_type = account_config["type"]
            currency = account_config["currency"]

            print(f"\n  Checking: {name} ({account_type.value}, {currency})")

            if await check_account_exists(db, name):
                print(f"    SKIP: Already exists")
                skipped.append(name)
                continue

            if args.dry_run:
                print(f"    WOULD CREATE: {name}")
                created.append(name)
                continue

            account = await create_account(
                db=db,
                user_id=user_id,
                name=name,
                account_type=account_type,
                currency=currency,
            )
            print(f"    CREATED: ID={account.id}")
            created.append(name)

        if not args.dry_run:
            await db.commit()

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"  Created: {len(created)}")
        print(f"  Skipped: {len(skipped)}")

        if created:
            print(f"\n  Created accounts:")
            for name in created:
                print(f"    - {name}")

        if skipped:
            print(f"\n  Skipped accounts (already exist):")
            for name in skipped:
                print(f"    - {name}")

        if args.dry_run:
            print("\n  [DRY RUN] No changes were made.")

        print("\n" + "=" * 60)
        print("NEXT STEPS")
        print("=" * 60)
        print("1. Upload PDFs to Extratos/<account_dir>/")
        print("2. Run batch import with --account flag:")
        print("   python -m scripts.batch_import_direct --account 'Alliance Investments'")
        print("   python -m scripts.batch_import_direct --account 'BTG Cayman 36595' --parser cayman")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
