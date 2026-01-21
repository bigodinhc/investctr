#!/usr/bin/env python3
"""
Fetch historical PTAX USD/BRL exchange rates from BCB (Banco Central do Brasil).

The PTAX rate is the official exchange rate used for financial calculations in Brazil.
This script fetches daily rates and stores them in the database.

BCB API: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/

Usage:
    python -m scripts.fetch_ptax_rates
    python -m scripts.fetch_ptax_rates --start-date 2021-01-01
    python -m scripts.fetch_ptax_rates --start-date 2021-01-01 --end-date 2024-12-31
"""

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session_maker
from app.models import ExchangeRate


BCB_PTAX_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"


async def fetch_ptax_from_bcb(start_date: date, end_date: date) -> list[dict]:
    """
    Fetch PTAX rates from BCB API for a date range.

    Returns list of dicts with date and rate.
    """
    # BCB expects dates in MM-DD-YYYY format
    start_str = start_date.strftime("%m-%d-%Y")
    end_str = end_date.strftime("%m-%d-%Y")

    params = {
        "@dataInicial": f"'{start_str}'",
        "@dataFinalCotacao": f"'{end_str}'",
        "$format": "json",
        "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao",
    }

    url = BCB_PTAX_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    rates = []
    for item in data.get("value", []):
        # Parse date from "2024-01-15 13:09:51.781"
        date_str = item.get("dataHoraCotacao", "")
        if not date_str:
            continue

        try:
            rate_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        # Use cotacaoVenda (sell rate) as it's typically used for conversions
        buy_rate = Decimal(str(item.get("cotacaoCompra", 0)))
        sell_rate = Decimal(str(item.get("cotacaoVenda", 0)))

        # Use average of buy and sell as the rate
        rate = (buy_rate + sell_rate) / 2

        rates.append({
            "date": rate_date,
            "rate": rate,
            "buy_rate": buy_rate,
            "sell_rate": sell_rate,
        })

    return rates


async def upsert_exchange_rate(
    db: AsyncSession,
    rate_date: date,
    from_currency: str,
    to_currency: str,
    rate: Decimal,
    source: str = "BCB_PTAX",
) -> bool:
    """Insert or update exchange rate. Returns True if created, False if updated."""
    query = select(ExchangeRate).where(
        and_(
            ExchangeRate.date == rate_date,
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
        )
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.rate = rate
        existing.source = source
        return False
    else:
        exchange_rate = ExchangeRate(
            date=rate_date,
            from_currency=from_currency,
            to_currency=to_currency,
            rate=rate,
            source=source,
        )
        db.add(exchange_rate)
        return True


async def main():
    parser = argparse.ArgumentParser(description="Fetch PTAX USD/BRL rates from BCB")
    parser.add_argument(
        "--start-date",
        type=str,
        default="2021-01-01",
        help="Start date (YYYY-MM-DD), default: 2021-01-01",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD), default: today",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch rates but don't save to database",
    )
    args = parser.parse_args()

    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else date.today()

    print("=" * 70)
    print("FETCH PTAX USD/BRL EXCHANGE RATES")
    print("=" * 70)
    print(f"Period: {start_date} to {end_date}")
    print(f"Source: BCB (Banco Central do Brasil)")
    print()

    # BCB API has a limit, so we fetch in chunks of 1 year
    all_rates = []
    current_start = start_date

    while current_start <= end_date:
        current_end = min(current_start + timedelta(days=365), end_date)

        print(f"  Fetching {current_start} to {current_end}...")

        try:
            rates = await fetch_ptax_from_bcb(current_start, current_end)
            all_rates.extend(rates)
            print(f"    Got {len(rates)} rates")
        except Exception as e:
            print(f"    ERROR: {e}")

        current_start = current_end + timedelta(days=1)

    print(f"\nTotal rates fetched: {len(all_rates)}")

    if not all_rates:
        print("No rates to save.")
        return

    # Show sample rates
    print("\nSample rates:")
    for rate in all_rates[:5]:
        print(f"  {rate['date']}: USD/BRL = {rate['rate']:.4f}")
    if len(all_rates) > 5:
        print(f"  ...")
        for rate in all_rates[-3:]:
            print(f"  {rate['date']}: USD/BRL = {rate['rate']:.4f}")

    if args.dry_run:
        print("\n[DRY RUN] No rates saved to database.")
        return

    # Save to database
    print("\nSaving to database...")

    session_maker = get_session_maker()

    async with session_maker() as db:
        created = 0
        updated = 0

        for rate_data in all_rates:
            is_new = await upsert_exchange_rate(
                db=db,
                rate_date=rate_data["date"],
                from_currency="USD",
                to_currency="BRL",
                rate=rate_data["rate"],
                source="BCB_PTAX",
            )
            if is_new:
                created += 1
            else:
                updated += 1

        await db.commit()

        print(f"\nRates created: {created}")
        print(f"Rates updated: {updated}")

        # Show latest rate
        query = select(ExchangeRate).where(
            and_(
                ExchangeRate.from_currency == "USD",
                ExchangeRate.to_currency == "BRL",
            )
        ).order_by(ExchangeRate.date.desc()).limit(1)
        result = await db.execute(query)
        latest = result.scalar_one_or_none()

        if latest:
            print(f"\nLatest rate in database:")
            print(f"  {latest.date}: USD/BRL = {latest.rate:.4f}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Run portfolio snapshot backfill: python -m scripts.backfill_portfolio_snapshots")
    print("2. Run consolidation: python -m scripts.consolidate_portfolio --verbose")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
