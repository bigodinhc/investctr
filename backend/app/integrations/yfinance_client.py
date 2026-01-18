"""
Yahoo Finance client for fetching market data.

This module provides functions to fetch quotes from Yahoo Finance
for Brazilian assets (B3) and other markets.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import yfinance as yf

from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Thread pool for running sync yfinance calls
_executor = ThreadPoolExecutor(max_workers=5)


@dataclass
class QuoteData:
    """Data class representing a quote from Yahoo Finance."""

    ticker: str
    date: date
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    close: Decimal
    adjusted_close: Decimal | None
    volume: int | None
    currency: str


def normalize_brazilian_ticker(ticker: str) -> str:
    """
    Normalize a Brazilian ticker for Yahoo Finance.

    Yahoo Finance requires Brazilian tickers to have the .SA suffix
    for B3 (Bovespa) listed assets.

    Args:
        ticker: The original ticker symbol

    Returns:
        Ticker with .SA suffix if needed

    Examples:
        >>> normalize_brazilian_ticker("PETR4")
        'PETR4.SA'
        >>> normalize_brazilian_ticker("PETR4.SA")
        'PETR4.SA'
        >>> normalize_brazilian_ticker("AAPL")
        'AAPL'
    """
    # Already has a suffix (e.g., .SA, .L, .F)
    if "." in ticker:
        return ticker

    # Common Brazilian ticker patterns (3-4 letters + 1-2 numbers)
    # Examples: PETR4, VALE3, ITUB4, BBDC4, B3SA3, HGLG11 (FII)
    # Also includes: TAEE11, BBAS3, WEGE3, etc.
    ticker_upper = ticker.upper()

    # Check if it looks like a Brazilian ticker
    # Brazilian tickers: 4-6 chars, ending with 1-2 digits
    if len(ticker_upper) >= 4 and len(ticker_upper) <= 6:
        # Check if last 1-2 chars are digits
        if ticker_upper[-1].isdigit():
            # Check if the rest (before digits) are letters
            letter_part = ticker_upper.rstrip("0123456789")
            if len(letter_part) >= 3 and letter_part.isalpha():
                return f"{ticker_upper}.SA"

    return ticker


def _fetch_quote_sync(ticker: str, start_date: date, end_date: date) -> list[QuoteData]:
    """
    Synchronously fetch quotes from Yahoo Finance.

    Args:
        ticker: Ticker symbol (with proper suffix)
        start_date: Start date for historical data
        end_date: End date for historical data

    Returns:
        List of QuoteData objects

    Raises:
        ExternalServiceError: If the API call fails
    """
    try:
        yf_ticker = yf.Ticker(ticker)

        # Fetch historical data
        history = yf_ticker.history(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            auto_adjust=False,  # Get unadjusted prices + adj close
        )

        if history.empty:
            logger.warning("yfinance_empty_response", ticker=ticker)
            return []

        # Get currency from ticker info (with fallback)
        try:
            info = yf_ticker.info
            currency = info.get("currency", "BRL")
        except Exception:
            # Default to BRL for .SA tickers
            currency = "BRL" if ticker.endswith(".SA") else "USD"

        quotes = []
        for idx, row in history.iterrows():
            quote_date = idx.date() if hasattr(idx, "date") else idx

            # Handle NaN values
            def safe_decimal(value: Any) -> Decimal | None:
                if value is None or (hasattr(value, "__float__") and str(value) == "nan"):
                    return None
                try:
                    return Decimal(str(float(value)))
                except (ValueError, TypeError):
                    return None

            def safe_int(value: Any) -> int | None:
                if value is None or (hasattr(value, "__float__") and str(value) == "nan"):
                    return None
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None

            close_value = safe_decimal(row.get("Close"))
            if close_value is None:
                continue  # Skip rows without close price

            quotes.append(
                QuoteData(
                    ticker=ticker.replace(".SA", ""),  # Store without suffix
                    date=quote_date,
                    open=safe_decimal(row.get("Open")),
                    high=safe_decimal(row.get("High")),
                    low=safe_decimal(row.get("Low")),
                    close=close_value,
                    adjusted_close=safe_decimal(row.get("Adj Close")),
                    volume=safe_int(row.get("Volume")),
                    currency=currency,
                )
            )

        logger.info(
            "yfinance_fetch_success",
            ticker=ticker,
            quotes_count=len(quotes),
        )

        return quotes

    except Exception as e:
        logger.error(
            "yfinance_fetch_error",
            ticker=ticker,
            error=str(e),
        )
        raise ExternalServiceError("yfinance", str(e))


async def fetch_quote(
    ticker: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[QuoteData]:
    """
    Fetch quote data for a single ticker.

    Args:
        ticker: Ticker symbol (will be normalized for Brazilian assets)
        start_date: Start date (defaults to today)
        end_date: End date (defaults to today)

    Returns:
        List of QuoteData objects

    Example:
        >>> quotes = await fetch_quote("PETR4")
        >>> print(quotes[0].close)
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date

    # Normalize ticker for Yahoo Finance
    yf_ticker = normalize_brazilian_ticker(ticker)

    logger.info(
        "yfinance_fetch_start",
        original_ticker=ticker,
        yf_ticker=yf_ticker,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Run sync function in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _executor,
        _fetch_quote_sync,
        yf_ticker,
        start_date,
        end_date,
    )


async def fetch_quotes_batch(
    tickers: list[str],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, list[QuoteData]]:
    """
    Fetch quotes for multiple tickers in parallel.

    Args:
        tickers: List of ticker symbols
        start_date: Start date (defaults to today)
        end_date: End date (defaults to today)

    Returns:
        Dictionary mapping ticker to list of QuoteData

    Example:
        >>> quotes = await fetch_quotes_batch(["PETR4", "VALE3", "ITUB4"])
        >>> for ticker, data in quotes.items():
        ...     print(f"{ticker}: {data[0].close if data else 'N/A'}")
    """
    if not tickers:
        return {}

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date

    logger.info(
        "yfinance_batch_fetch_start",
        tickers_count=len(tickers),
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )

    # Create tasks for all tickers
    tasks = [fetch_quote(ticker, start_date, end_date) for ticker in tickers]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build result dictionary
    quotes_dict: dict[str, list[QuoteData]] = {}
    success_count = 0
    error_count = 0

    for ticker, result in zip(tickers, results, strict=True):
        if isinstance(result, Exception):
            logger.warning(
                "yfinance_batch_ticker_error",
                ticker=ticker,
                error=str(result),
            )
            quotes_dict[ticker] = []
            error_count += 1
        else:
            quotes_dict[ticker] = result
            if result:
                success_count += 1
            else:
                error_count += 1

    logger.info(
        "yfinance_batch_fetch_complete",
        total_tickers=len(tickers),
        success_count=success_count,
        error_count=error_count,
    )

    return quotes_dict


async def get_current_price(ticker: str) -> Decimal | None:
    """
    Get the most recent closing price for a ticker.

    Args:
        ticker: Ticker symbol

    Returns:
        Most recent closing price or None if not available
    """
    quotes = await fetch_quote(ticker)
    if quotes:
        return quotes[-1].close
    return None
