"""
Tesouro Direto (Brazilian Treasury) data client.

Fetches historical prices and rates for Brazilian government bonds.
Source: https://www.tesourodireto.com.br/titulos/historico-de-precos-e-taxas.htm
"""

import logging
from datetime import date
from decimal import Decimal
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Tesouro Direto data URLs
TESOURO_PRECOS_URL = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PresosETaxasTesouroDireto.csv"
TESOURO_VENDAS_URL = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/e5f90e3a-8f8d-4895-9c56-4bb2f7877920/download/VendasTesouroDireto.csv"

# Alternative URLs (backup)
TESOURO_ALT_URL = "https://www.tesourodireto.com.br/titulos/historico-de-precos-e-taxas.htm"


# Mapping of internal tickers to Tesouro Direto names
TICKER_TO_TESOURO_NAME = {
    # LFT - Tesouro Selic
    "LFT": "Tesouro Selic",
    "TESOURO-SELIC": "Tesouro Selic",

    # NTN-B - Tesouro IPCA+
    "NTNB": "Tesouro IPCA+",
    "NTN-B": "Tesouro IPCA+",
    "TESOURO-IPCA": "Tesouro IPCA+",

    # NTN-B Principal
    "NTNB-PRINC": "Tesouro IPCA+ com Juros Semestrais",

    # NTN-F - Tesouro Prefixado com Juros
    "NTNF": "Tesouro Prefixado com Juros Semestrais",
    "NTN-F": "Tesouro Prefixado com Juros Semestrais",

    # LTN - Tesouro Prefixado
    "LTN": "Tesouro Prefixado",
    "TESOURO-PREFIXADO": "Tesouro Prefixado",
}


def fetch_tesouro_prices() -> pd.DataFrame:
    """
    Fetch historical prices and rates from Tesouro Direto.

    Returns DataFrame with columns:
    - Tipo Titulo
    - Data Vencimento
    - Data Base
    - Taxa Compra Manha
    - Taxa Venda Manha
    - PU Compra Manha
    - PU Venda Manha
    - PU Base Manha
    """
    logger.info("Fetching Tesouro Direto historical prices...")

    try:
        response = requests.get(TESOURO_PRECOS_URL, timeout=120)
        response.raise_for_status()

        # The CSV uses semicolon separator and has Brazilian number format
        df = pd.read_csv(
            StringIO(response.text),
            sep=";",
            encoding="latin1",
            decimal=",",
            thousands=".",
        )

        # Rename columns for easier access
        df.columns = df.columns.str.strip()

        # Convert date columns
        date_cols = ["Data Vencimento", "Data Base"]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")

        logger.info(f"Loaded {len(df)} Tesouro Direto price records")
        return df

    except Exception as e:
        logger.error(f"Error fetching Tesouro Direto prices: {e}")
        raise


def parse_ticker_maturity(ticker: str) -> tuple[str, date | None]:
    """
    Parse internal ticker to extract bond type and maturity.

    Examples:
        LFT-MAR23 -> ("LFT", 2023-03-01)
        NTNB-AGO28 -> ("NTNB", 2028-08-01)
        NTNF-JAN27 -> ("NTNF", 2027-01-01)
    """
    # Month mapping (Portuguese abbreviations)
    month_map = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4,
        "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8,
        "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
    }

    parts = ticker.upper().split("-")

    if len(parts) < 2:
        return ticker, None

    bond_type = parts[0]
    maturity_str = parts[1]

    # Try to parse maturity (e.g., "AGO28" -> August 2028)
    try:
        month_abbr = maturity_str[:3]
        year_str = maturity_str[3:]

        if month_abbr in month_map:
            month = month_map[month_abbr]

            # Handle 2-digit year
            if len(year_str) == 2:
                year = 2000 + int(year_str)
            else:
                year = int(year_str)

            # Tesouro titles typically mature on the 1st or 15th
            maturity = date(year, month, 1)
            return bond_type, maturity

    except (ValueError, KeyError):
        pass

    return bond_type, None


def get_tesouro_name(ticker: str) -> str | None:
    """Get Tesouro Direto official name from internal ticker."""
    bond_type, _ = parse_ticker_maturity(ticker)
    return TICKER_TO_TESOURO_NAME.get(bond_type)


def fetch_bond_prices(
    ticker: str,
    start_date: date,
    end_date: date | None = None,
) -> list[dict]:
    """
    Fetch historical prices for a specific Treasury bond.

    Args:
        ticker: Internal ticker (e.g., "LFT-MAR23", "NTNB-AGO28")
        start_date: Start date for historical data
        end_date: End date (defaults to today)

    Returns:
        List of dicts with keys: date, close (PU), rate
    """
    if end_date is None:
        end_date = date.today()

    # Parse ticker
    bond_type, maturity = parse_ticker_maturity(ticker)
    tesouro_name = TICKER_TO_TESOURO_NAME.get(bond_type)

    if not tesouro_name:
        logger.warning(f"Unknown bond type: {bond_type}")
        return []

    # Fetch all prices
    df = fetch_tesouro_prices()

    if df.empty:
        return []

    # Filter by bond type (partial match)
    mask = df["Tipo Titulo"].str.contains(tesouro_name, case=False, na=False)

    # Filter by maturity if available
    if maturity:
        # Match maturity year and month
        mask &= (df["Data Vencimento"].dt.year == maturity.year)
        mask &= (df["Data Vencimento"].dt.month == maturity.month)

    filtered = df[mask]

    if filtered.empty:
        logger.warning(f"No data found for {ticker} ({tesouro_name}, maturity={maturity})")
        return []

    # Filter by date range
    filtered = filtered[
        (filtered["Data Base"].dt.date >= start_date) &
        (filtered["Data Base"].dt.date <= end_date)
    ]

    # Sort by date
    filtered = filtered.sort_values("Data Base")

    # Convert to standard format
    quotes = []
    for _, row in filtered.iterrows():
        quote = {
            "date": row["Data Base"].date(),
            "close": None,
            "rate": None,
        }

        # Use PU Venda (selling price) as the close price
        pu_col = "PU Venda Manha" if "PU Venda Manha" in row else "PU Base Manha"
        if pu_col in row and pd.notna(row[pu_col]):
            quote["close"] = Decimal(str(row[pu_col]))

        # Get rate
        rate_col = "Taxa Venda Manha" if "Taxa Venda Manha" in row else "Taxa Compra Manha"
        if rate_col in row and pd.notna(row[rate_col]):
            quote["rate"] = Decimal(str(row[rate_col]))

        if quote["close"] is not None:
            quotes.append(quote)

    logger.info(f"Found {len(quotes)} price records for {ticker}")
    return quotes


def get_cdi_rate(target_date: date | None = None) -> Decimal | None:
    """
    Get CDI rate for CDB valuation.

    For CDBs, we calculate value as: principal * (1 + CDI * rate_percent) ^ (days/252)
    """
    # For now, return a placeholder
    # In production, this should fetch from BCB API
    # https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados?formato=json
    return Decimal("0.1365")  # ~13.65% CDI (approximate)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        ticker = "NTNB-AGO28"

    print(f"\nFetching prices for {ticker}...")
    start = date(2021, 5, 1)
    end = date.today()

    quotes = fetch_bond_prices(ticker, start, end)
    print(f"\nFound {len(quotes)} quotes:")

    for q in quotes[:10]:
        print(f"  {q['date']}: PU={q['close']}, Rate={q['rate']}")

    if len(quotes) > 10:
        print(f"  ... and {len(quotes) - 10} more")
