#!/usr/bin/env python3
"""
Management script to recalculate all positions and display P&L summary.

Usage:
    python -m scripts.recalculate_positions

Or from backend directory:
    python scripts/recalculate_positions.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Account, Asset
from app.services.position_service import PositionService
from app.services.pnl_service import PnLService, PnLType


async def recalculate_and_report():
    """Recalculate all positions and display P&L summary."""

    async with AsyncSessionLocal() as db:
        print("=" * 70)
        print("RECALCULATING POSITIONS WITH LONG/SHORT NETTING MODEL")
        print("=" * 70)

        # Get all accounts
        accounts_result = await db.execute(select(Account))
        accounts = list(accounts_result.scalars().all())

        if not accounts:
            print("\nNo accounts found in database.")
            return

        print(f"\nFound {len(accounts)} account(s)\n")

        position_service = PositionService(db)
        pnl_service = PnLService(db)

        total_long_positions = 0
        total_short_positions = 0

        for account in accounts:
            print(f"\n{'='*70}")
            print(f"Account: {account.name} (ID: {account.id})")
            print(f"Type: {account.type.value}")
            print("-" * 70)

            # Recalculate positions
            positions = await position_service.recalculate_account_positions(account.id)

            long_count = sum(1 for p in positions if p.position_type.value == "long")
            short_count = sum(1 for p in positions if p.position_type.value == "short")

            total_long_positions += long_count
            total_short_positions += short_count

            print(f"Positions recalculated: {len(positions)}")
            print(f"  - LONG positions: {long_count}")
            print(f"  - SHORT positions: {short_count}")

            # Show SHORT positions if any
            short_positions = [p for p in positions if p.position_type.value == "short"]
            if short_positions:
                print("\n  SHORT positions detected:")
                for pos in short_positions:
                    # Get asset ticker
                    asset_result = await db.execute(
                        select(Asset).where(Asset.id == pos.asset_id)
                    )
                    asset = asset_result.scalar_one_or_none()
                    ticker = asset.ticker if asset else "UNKNOWN"
                    print(f"    - {ticker}: qty={pos.quantity}, avg_price={pos.avg_price:.2f}")

            # Calculate P&L for this account
            pnl_summary = await pnl_service.calculate_realized_pnl(account_id=account.id)

            long_close_pnl = sum(
                e.realized_pnl for e in pnl_summary.entries
                if e.pnl_type == PnLType.LONG_CLOSE
            )
            short_close_pnl = sum(
                e.realized_pnl for e in pnl_summary.entries
                if e.pnl_type == PnLType.SHORT_CLOSE
            )
            long_close_count = sum(
                1 for e in pnl_summary.entries
                if e.pnl_type == PnLType.LONG_CLOSE
            )
            short_close_count = sum(
                1 for e in pnl_summary.entries
                if e.pnl_type == PnLType.SHORT_CLOSE
            )

            print("\nRealized P&L Summary:")
            print(f"  Total Realized P&L: R$ {pnl_summary.total_realized_pnl:,.2f}")
            print(f"  - From LONG closes ({long_close_count}): R$ {long_close_pnl:,.2f}")
            print(f"  - From SHORT closes ({short_close_count}): R$ {short_close_pnl:,.2f}")
            print(f"  Total transactions: {pnl_summary.transaction_count}")
            print(f"  Total fees: R$ {pnl_summary.total_fees:,.2f}")

        # Overall summary
        print("\n" + "=" * 70)
        print("OVERALL SUMMARY")
        print("=" * 70)
        print(f"Total LONG positions: {total_long_positions}")
        print(f"Total SHORT positions: {total_short_positions}")

        # Get overall P&L across all accounts
        overall_pnl = await pnl_service.calculate_realized_pnl()

        overall_long_pnl = sum(
            e.realized_pnl for e in overall_pnl.entries
            if e.pnl_type == PnLType.LONG_CLOSE
        )
        overall_short_pnl = sum(
            e.realized_pnl for e in overall_pnl.entries
            if e.pnl_type == PnLType.SHORT_CLOSE
        )

        print(f"\nTotal Realized P&L: R$ {overall_pnl.total_realized_pnl:,.2f}")
        print(f"  - From LONG closes: R$ {overall_long_pnl:,.2f}")
        print(f"  - From SHORT closes: R$ {overall_short_pnl:,.2f}")
        print("=" * 70)

        # Show top 10 P&L events by absolute value
        print("\nTop 10 P&L Events (by absolute value):")
        sorted_entries = sorted(
            overall_pnl.entries,
            key=lambda e: abs(e.realized_pnl),
            reverse=True
        )[:10]

        for i, entry in enumerate(sorted_entries, 1):
            pnl_type_str = "LONG" if entry.pnl_type == PnLType.LONG_CLOSE else "SHORT"
            print(
                f"  {i}. {entry.ticker or 'N/A'}: "
                f"R$ {entry.realized_pnl:+,.2f} ({pnl_type_str} close, "
                f"{entry.quantity} units @ {entry.close_price:.2f})"
            )


if __name__ == "__main__":
    asyncio.run(recalculate_and_report())
