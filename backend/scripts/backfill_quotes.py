#!/usr/bin/env python3
"""
Backfill historical quotes from multiple sources for all assets with transactions.

Data sources:
- Yahoo Finance: Stocks, FIIs, ETFs, BDRs
- Tesouro Direto: Treasury bonds (LFT, NTN-B, NTN-F)
- CVM: Investment funds (via CNPJ)

Usage:
    python -m scripts.backfill_quotes

Or from backend directory:
    python scripts/backfill_quotes.py
"""

import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, distinct

from app.database import get_session_maker
from app.models import Asset, Transaction, Position, Quote
from app.services.quote_service import QuoteService


# Backfill start date
START_DATE = date(2021, 5, 1)

# Known fund CNPJs (search using: python scripts/search_fund_cnpj.py "BTG")
# Update these with actual CNPJs from CVM search
FUND_CNPJS = {
    # Example: "BTG-CREDCORP": "12.345.678/0001-90",
    # "BTG-YIELD-DI": "98.765.432/0001-10",
}


async def get_assets_by_type(db) -> dict[str, list[Asset]]:
    """
    Get all assets that need historical quotes, grouped by type.

    Returns dict with keys: stocks, treasury, funds, bonds
    """
    # Get asset IDs from positions and transactions
    positions_query = select(distinct(Position.asset_id))
    positions_result = await db.execute(positions_query)
    position_asset_ids = set(positions_result.scalars().all())

    transactions_query = select(distinct(Transaction.asset_id))
    transactions_result = await db.execute(transactions_query)
    transaction_asset_ids = set(transactions_result.scalars().all())

    all_asset_ids = position_asset_ids | transaction_asset_ids

    if not all_asset_ids:
        return {"stocks": [], "treasury": [], "funds": [], "bonds": []}

    # Get assets
    assets_query = select(Asset).where(Asset.id.in_(all_asset_ids))
    assets_result = await db.execute(assets_query)
    assets = list(assets_result.scalars().all())

    # Group by type
    result = {"stocks": [], "treasury": [], "funds": [], "bonds": []}

    for asset in assets:
        asset_type = asset.asset_type or "stock"

        if asset_type == "treasury":
            result["treasury"].append(asset)
        elif asset_type == "fund":
            result["funds"].append(asset)
        elif asset_type == "bond":
            result["bonds"].append(asset)
        else:
            # stocks, fii, etf, bdr, etc. - use yfinance
            result["stocks"].append(asset)

    return result


async def backfill_stocks_yfinance(db, assets: list[Asset], quote_service: QuoteService) -> int:
    """Backfill stock quotes from Yahoo Finance."""
    if not assets:
        return 0

    tickers = [a.ticker for a in assets if a.ticker]
    print(f"\n[YFINANCE] Processing {len(tickers)} stocks/FIIs/ETFs...")

    # Process in batches
    batch_size = 10
    total_quotes = 0
    failed = []

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(tickers) + batch_size - 1) // batch_size

        print(f"  Batch {batch_num}/{total_batches}: {batch}")

        try:
            quotes = await quote_service.fetch_and_save_quotes(
                tickers=batch,
                start_date=START_DATE,
                end_date=date.today(),
            )
            total_quotes += len(quotes)
            print(f"    Saved {len(quotes)} quotes")
        except Exception as e:
            print(f"    Error: {e}")
            failed.extend(batch)

        if i + batch_size < len(tickers):
            await asyncio.sleep(1)

    if failed:
        print(f"  Failed: {failed}")

    return total_quotes


async def backfill_treasury_tesouro(db, assets: list[Asset]) -> int:
    """Backfill Treasury bond quotes from Tesouro Direto."""
    if not assets:
        return 0

    print(f"\n[TESOURO DIRETO] Processing {len(assets)} treasury bonds...")

    try:
        from app.integrations.tesouro_direto_client import fetch_bond_prices
    except ImportError as e:
        print(f"  Error importing tesouro_direto_client: {e}")
        return 0

    total_quotes = 0

    for asset in assets:
        ticker = asset.ticker
        print(f"  Processing {ticker}...")

        try:
            quotes_data = fetch_bond_prices(ticker, START_DATE, date.today())

            if not quotes_data:
                print(f"    No data found for {ticker}")
                continue

            # Save to database
            for q in quotes_data:
                if q["close"] is None:
                    continue

                # Check if exists
                existing = await db.execute(
                    select(Quote).where(
                        Quote.asset_id == asset.id,
                        Quote.date == q["date"]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Create quote
                quote = Quote(
                    asset_id=asset.id,
                    date=q["date"],
                    open=q["close"],
                    high=q["close"],
                    low=q["close"],
                    close=q["close"],
                    adjusted_close=q["close"],
                    volume=0,
                    source="tesouro_direto",
                )
                db.add(quote)
                total_quotes += 1

            print(f"    Saved {len(quotes_data)} quotes for {ticker}")

        except Exception as e:
            print(f"    Error processing {ticker}: {e}")

    return total_quotes


async def backfill_funds_cvm(db, assets: list[Asset]) -> int:
    """Backfill fund quotes from CVM."""
    if not assets:
        return 0

    print(f"\n[CVM] Processing {len(assets)} investment funds...")

    try:
        from app.integrations.cvm_client import get_fund_quote_history
    except ImportError as e:
        print(f"  Error importing cvm_client: {e}")
        return 0

    total_quotes = 0

    for asset in assets:
        ticker = asset.ticker
        cnpj = FUND_CNPJS.get(ticker)

        if not cnpj:
            print(f"  Skipping {ticker} - CNPJ not configured")
            print(f"    To find CNPJ, run: python scripts/search_fund_cnpj.py \"{asset.name}\"")
            continue

        print(f"  Processing {ticker} (CNPJ: {cnpj})...")

        try:
            quotes_data = get_fund_quote_history(cnpj, START_DATE, date.today())

            if not quotes_data:
                print(f"    No data found for {ticker}")
                continue

            # Save to database
            for q in quotes_data:
                if q["close"] is None:
                    continue

                # Check if exists
                existing = await db.execute(
                    select(Quote).where(
                        Quote.asset_id == asset.id,
                        Quote.date == q["date"]
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Create quote
                quote = Quote(
                    asset_id=asset.id,
                    date=q["date"],
                    open=q["close"],
                    high=q["close"],
                    low=q["close"],
                    close=q["close"],
                    adjusted_close=q["close"],
                    volume=q.get("volume") or 0,
                    source="cvm",
                )
                db.add(quote)
                total_quotes += 1

            print(f"    Saved quotes for {ticker}")

        except Exception as e:
            print(f"    Error processing {ticker}: {e}")

    return total_quotes


async def backfill_bonds_cdi(db, assets: list[Asset]) -> int:
    """
    Backfill CDB/bond quotes using CDI-based calculation.

    For CDBs, we calculate daily value based on CDI rate.
    Note: This is a simplified approach - actual values depend on
    the specific CDB terms and CDI history.
    """
    if not assets:
        return 0

    print(f"\n[CDB/BONDS] Processing {len(assets)} bonds...")
    print("  Note: CDBs are typically held to maturity and don't have market prices.")
    print("  Using face value / last transaction price as proxy.")

    total_quotes = 0

    for asset in assets:
        ticker = asset.ticker
        print(f"  Skipping {ticker} - CDBs typically use cost basis for NAV")
        # For now, we skip CDBs as they're usually valued at cost + accrued interest
        # The NAV calculation will use cost basis for these

    return total_quotes


async def backfill_quotes():
    """Backfill historical quotes for all assets from multiple sources."""
    session_maker = get_session_maker()

    async with session_maker() as db:
        print("=" * 70)
        print("BACKFILL HISTORICAL QUOTES (Multi-Source)")
        print("=" * 70)
        print(f"Start date: {START_DATE}")
        print(f"End date: {date.today()}")
        print()

        # Get assets grouped by type
        assets_by_type = await get_assets_by_type(db)

        print("Assets found:")
        print(f"  Stocks/FIIs/ETFs: {len(assets_by_type['stocks'])}")
        print(f"  Treasury bonds: {len(assets_by_type['treasury'])}")
        print(f"  Investment funds: {len(assets_by_type['funds'])}")
        print(f"  CDBs/Bonds: {len(assets_by_type['bonds'])}")

        # Initialize QuoteService for yfinance
        quote_service = QuoteService(db)

        # Process each type
        total = 0

        # 1. Stocks via yfinance
        total += await backfill_stocks_yfinance(db, assets_by_type["stocks"], quote_service)

        # 2. Treasury via Tesouro Direto
        total += await backfill_treasury_tesouro(db, assets_by_type["treasury"])

        # 3. Funds via CVM
        total += await backfill_funds_cvm(db, assets_by_type["funds"])

        # 4. Bonds (CDBs) - skip for now
        total += await backfill_bonds_cdi(db, assets_by_type["bonds"])

        # Commit all changes
        await db.commit()

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        from sqlalchemy import func

        count_query = select(func.count()).select_from(Quote)
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()

        print(f"Total new quotes saved: {total}")
        print(f"Total quotes in database: {total_count}")

        # Check unfilled assets
        print("\nAssets without quotes:")
        for asset in assets_by_type["funds"]:
            if asset.ticker not in FUND_CNPJS:
                print(f"  - {asset.ticker}: Need CNPJ configuration")

        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(backfill_quotes())
