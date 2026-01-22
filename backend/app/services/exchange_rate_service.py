"""
Exchange Rate Service for currency conversion.

Provides functions to:
- Get PTAX rates from database
- Convert amounts between currencies
- Fetch and store PTAX rates from BCB
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import ExchangeRate

logger = get_logger(__name__)


BCB_PTAX_URL = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"


class ExchangeRateService:
    """Service for managing exchange rates and currency conversion."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_ptax(
        self,
        target_date: date,
        fallback_days: int = 7,
    ) -> Optional[Decimal]:
        """
        Get PTAX USD/BRL rate for a specific date.

        If no rate exists for the exact date, returns the most recent
        rate up to fallback_days before.

        Args:
            target_date: Target date for the rate
            fallback_days: Number of days to look back for a rate

        Returns:
            PTAX rate or None if not found
        """
        min_date = target_date - timedelta(days=fallback_days)

        query = (
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == "USD",
                    ExchangeRate.to_currency == "BRL",
                    ExchangeRate.date <= target_date,
                    ExchangeRate.date >= min_date,
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        rate_record = result.scalar_one_or_none()

        if rate_record:
            logger.debug(
                "exchange_rate_found",
                target_date=target_date.isoformat(),
                rate_date=rate_record.date.isoformat(),
                rate=float(rate_record.rate),
            )
            return rate_record.rate

        logger.warning(
            "exchange_rate_not_found",
            target_date=target_date.isoformat(),
            fallback_days=fallback_days,
        )
        return None

    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        target_date: date,
        fallback_days: int = 7,
    ) -> Optional[Decimal]:
        """
        Get exchange rate between two currencies for a specific date.

        Args:
            from_currency: Source currency (e.g., "USD")
            to_currency: Target currency (e.g., "BRL")
            target_date: Target date for the rate
            fallback_days: Number of days to look back for a rate

        Returns:
            Exchange rate or None if not found
        """
        # Handle identity conversion
        if from_currency == to_currency:
            return Decimal("1.0")

        min_date = target_date - timedelta(days=fallback_days)

        query = (
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == from_currency,
                    ExchangeRate.to_currency == to_currency,
                    ExchangeRate.date <= target_date,
                    ExchangeRate.date >= min_date,
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        rate_record = result.scalar_one_or_none()

        if rate_record:
            return rate_record.rate

        # Try inverse rate
        query_inverse = (
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == to_currency,
                    ExchangeRate.to_currency == from_currency,
                    ExchangeRate.date <= target_date,
                    ExchangeRate.date >= min_date,
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )

        result_inverse = await self.db.execute(query_inverse)
        rate_record_inverse = result_inverse.scalar_one_or_none()

        if rate_record_inverse and rate_record_inverse.rate != Decimal("0"):
            return Decimal("1") / rate_record_inverse.rate

        return None

    async def convert_to_brl(
        self,
        amount: Decimal,
        from_currency: str,
        target_date: date,
    ) -> tuple[Decimal, Decimal | None]:
        """
        Convert an amount to BRL using the exchange rate for the target date.

        Args:
            amount: Amount to convert
            from_currency: Source currency (e.g., "USD")
            target_date: Date for the exchange rate

        Returns:
            Tuple of (converted_amount_brl, exchange_rate_used)
            If from_currency is already BRL, returns (amount, None)
        """
        if from_currency == "BRL":
            return amount, None

        rate = await self.get_exchange_rate(from_currency, "BRL", target_date)

        if rate is None:
            logger.warning(
                "convert_to_brl_no_rate",
                from_currency=from_currency,
                amount=float(amount),
                target_date=target_date.isoformat(),
            )
            # Return original amount if no rate found (will be flagged as unconverted)
            return amount, None

        converted = amount * rate
        logger.debug(
            "convert_to_brl_success",
            from_currency=from_currency,
            amount=float(amount),
            rate=float(rate),
            converted=float(converted),
        )
        return converted, rate

    async def convert_from_brl(
        self,
        amount: Decimal,
        to_currency: str,
        target_date: date,
    ) -> tuple[Decimal, Decimal | None]:
        """
        Convert an amount from BRL to another currency.

        Args:
            amount: Amount in BRL
            to_currency: Target currency (e.g., "USD")
            target_date: Date for the exchange rate

        Returns:
            Tuple of (converted_amount, exchange_rate_used)
            If to_currency is BRL, returns (amount, None)
        """
        if to_currency == "BRL":
            return amount, None

        rate = await self.get_exchange_rate("BRL", to_currency, target_date)

        if rate is None:
            logger.warning(
                "convert_from_brl_no_rate",
                to_currency=to_currency,
                amount=float(amount),
                target_date=target_date.isoformat(),
            )
            return amount, None

        converted = amount * rate
        return converted, rate

    async def fetch_and_store_ptax(
        self,
        start_date: date,
        end_date: date,
    ) -> int:
        """
        Fetch PTAX rates from BCB and store in database.

        Args:
            start_date: Start date for fetching
            end_date: End date for fetching

        Returns:
            Number of rates stored/updated
        """
        logger.info(
            "fetch_ptax_start",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        rates = await self._fetch_from_bcb(start_date, end_date)

        count = 0
        for rate_data in rates:
            await self._upsert_rate(
                rate_date=rate_data["date"],
                from_currency="USD",
                to_currency="BRL",
                rate=rate_data["rate"],
                source="BCB_PTAX",
            )
            count += 1

        await self.db.commit()

        logger.info(
            "fetch_ptax_complete",
            rates_stored=count,
        )

        return count

    async def _fetch_from_bcb(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Fetch PTAX rates from BCB API."""
        # BCB expects dates in MM-DD-YYYY format
        start_str = start_date.strftime("%m-%d-%Y")
        end_str = end_date.strftime("%m-%d-%Y")

        params = {
            "@dataInicial": f"'{start_str}'",
            "@dataFinalCotacao": f"'{end_str}'",
            "$format": "json",
            "$select": "cotacaoCompra,cotacaoVenda,dataHoraCotacao",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BCB_PTAX_URL, params=params)
            response.raise_for_status()
            data = response.json()

        rates_by_date = {}
        for item in data.get("value", []):
            date_str = item.get("dataHoraCotacao", "")
            if not date_str:
                continue

            try:
                from datetime import datetime
                rate_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue

            buy_rate = Decimal(str(item.get("cotacaoCompra", 0)))
            sell_rate = Decimal(str(item.get("cotacaoVenda", 0)))
            rate = (buy_rate + sell_rate) / 2

            rates_by_date[rate_date] = {
                "date": rate_date,
                "rate": rate,
            }

        return list(rates_by_date.values())

    async def _upsert_rate(
        self,
        rate_date: date,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: str = "BCB_PTAX",
    ) -> None:
        """Insert or update exchange rate."""
        query = select(ExchangeRate).where(
            and_(
                ExchangeRate.date == rate_date,
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
            )
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.rate = rate
            existing.source = source
        else:
            exchange_rate = ExchangeRate(
                date=rate_date,
                from_currency=from_currency,
                to_currency=to_currency,
                rate=rate,
                source=source,
            )
            self.db.add(exchange_rate)

    async def get_latest_ptax(self) -> tuple[date, Decimal] | None:
        """
        Get the most recent PTAX rate in the database.

        Returns:
            Tuple of (date, rate) or None if no rates exist
        """
        query = (
            select(ExchangeRate)
            .where(
                and_(
                    ExchangeRate.from_currency == "USD",
                    ExchangeRate.to_currency == "BRL",
                )
            )
            .order_by(ExchangeRate.date.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        rate_record = result.scalar_one_or_none()

        if rate_record:
            return rate_record.date, rate_record.rate

        return None


# Utility functions for use outside the service context

async def get_ptax(
    db: AsyncSession,
    target_date: date,
) -> Decimal | None:
    """
    Utility function to get PTAX rate.

    Args:
        db: Database session
        target_date: Target date

    Returns:
        PTAX rate or None
    """
    service = ExchangeRateService(db)
    return await service.get_ptax(target_date)


async def convert_to_brl(
    db: AsyncSession,
    amount: Decimal,
    from_currency: str,
    target_date: date,
) -> tuple[Decimal, Decimal | None]:
    """
    Utility function to convert amount to BRL.

    Args:
        db: Database session
        amount: Amount to convert
        from_currency: Source currency
        target_date: Date for exchange rate

    Returns:
        Tuple of (converted_amount, rate_used)
    """
    service = ExchangeRateService(db)
    return await service.convert_to_brl(amount, from_currency, target_date)
