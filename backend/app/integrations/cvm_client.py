"""
CVM (Comissão de Valores Mobiliários) data client.

Fetches fund quota (valor da cota) historical data from CVM open data portal.
Source: https://dados.cvm.gov.br/dataset/fi-doc-inf_diario
"""

import logging
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
from zipfile import ZipFile

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# CVM data URLs
CVM_INF_DIARIO_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
CVM_CAD_FI_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"


def fetch_fund_cadastro() -> pd.DataFrame:
    """
    Fetch fund cadastral data from CVM.

    Returns DataFrame with columns:
    - CNPJ_FUNDO
    - DENOM_SOCIAL (fund name)
    - SIT (situation)
    - TP_FUNDO (fund type)
    - etc.
    """
    logger.info("Fetching CVM fund cadastro...")

    try:
        response = requests.get(CVM_CAD_FI_URL, timeout=60)
        response.raise_for_status()

        df = pd.read_csv(
            StringIO(response.text),
            sep=";",
            encoding="latin1",
            dtype=str,
        )

        logger.info(f"Loaded {len(df)} funds from CVM cadastro")
        return df

    except Exception as e:
        logger.error(f"Error fetching CVM cadastro: {e}")
        raise


def search_fund_by_name(name_pattern: str) -> pd.DataFrame:
    """
    Search for funds by name pattern.

    Args:
        name_pattern: Partial fund name to search

    Returns:
        DataFrame with matching funds
    """
    df = fetch_fund_cadastro()

    # Search in DENOM_SOCIAL column
    mask = df["DENOM_SOCIAL"].str.contains(
        name_pattern,
        case=False,
        na=False
    )

    return df[mask][["CNPJ_FUNDO", "DENOM_SOCIAL", "SIT", "TP_FUNDO"]]


def fetch_fund_quotes_month(year: int, month: int) -> pd.DataFrame:
    """
    Fetch fund daily quotes for a specific month.

    Args:
        year: Year (YYYY)
        month: Month (1-12)

    Returns:
        DataFrame with columns:
        - CNPJ_FUNDO
        - DT_COMPTC (date)
        - VL_QUOTA (quota value)
        - VL_PATRIM_LIQ (net worth)
        - NR_COTST (number of shareholders)
    """
    date_str = f"{year}{month:02d}"
    url = f"{CVM_INF_DIARIO_URL}/inf_diario_fi_{date_str}.zip"

    logger.info(f"Fetching CVM fund quotes for {month:02d}/{year}...")

    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        # Extract CSV from ZIP
        with ZipFile(BytesIO(response.content)) as zip_file:
            csv_name = zip_file.namelist()[0]
            with zip_file.open(csv_name) as csv_file:
                df = pd.read_csv(
                    csv_file,
                    sep=";",
                    encoding="latin1",
                    dtype={
                        "CNPJ_FUNDO": str,
                        "DT_COMPTC": str,
                    },
                )

        # Convert date column
        df["DT_COMPTC"] = pd.to_datetime(df["DT_COMPTC"], format="%Y-%m-%d")

        # Convert numeric columns
        for col in ["VL_QUOTA", "VL_PATRIM_LIQ", "VL_TOTAL", "CAPTC_DIA", "RESG_DIA"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        logger.info(f"Loaded {len(df)} fund quote records for {month:02d}/{year}")
        return df

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"No data available for {month:02d}/{year}")
            return pd.DataFrame()
        raise
    except Exception as e:
        logger.error(f"Error fetching CVM quotes for {month:02d}/{year}: {e}")
        raise


def fetch_fund_quotes_range(
    cnpj: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """
    Fetch historical quotes for a specific fund.

    Args:
        cnpj: Fund CNPJ (with or without formatting)
        start_date: Start date
        end_date: End date

    Returns:
        DataFrame with daily quotes for the fund
    """
    # Normalize CNPJ (remove formatting)
    cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "")

    all_quotes = []

    # Iterate through months in range
    current = date(start_date.year, start_date.month, 1)
    while current <= end_date:
        try:
            month_data = fetch_fund_quotes_month(current.year, current.month)

            if not month_data.empty:
                # Filter by CNPJ
                fund_data = month_data[
                    month_data["CNPJ_FUNDO"].str.replace(r"[./-]", "", regex=True) == cnpj_clean
                ]

                if not fund_data.empty:
                    all_quotes.append(fund_data)

        except Exception as e:
            logger.warning(f"Error fetching {current.month:02d}/{current.year}: {e}")

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    if not all_quotes:
        return pd.DataFrame()

    result = pd.concat(all_quotes, ignore_index=True)

    # Filter by date range
    result = result[
        (result["DT_COMPTC"].dt.date >= start_date) &
        (result["DT_COMPTC"].dt.date <= end_date)
    ]

    return result.sort_values("DT_COMPTC")


def get_fund_quote_history(
    cnpj: str,
    start_date: date,
    end_date: date | None = None,
) -> list[dict]:
    """
    Get fund quote history in a normalized format.

    Args:
        cnpj: Fund CNPJ
        start_date: Start date
        end_date: End date (defaults to today)

    Returns:
        List of dicts with keys: date, close, volume
    """
    if end_date is None:
        end_date = date.today()

    df = fetch_fund_quotes_range(cnpj, start_date, end_date)

    if df.empty:
        return []

    quotes = []
    for _, row in df.iterrows():
        quotes.append({
            "date": row["DT_COMPTC"].date(),
            "close": Decimal(str(row["VL_QUOTA"])) if pd.notna(row["VL_QUOTA"]) else None,
            "volume": int(row["NR_COTST"]) if pd.notna(row.get("NR_COTST")) else None,
            "nav": Decimal(str(row["VL_PATRIM_LIQ"])) if pd.notna(row.get("VL_PATRIM_LIQ")) else None,
        })

    return quotes


# CNPJ mapping for known funds (can be extended)
KNOWN_FUND_CNPJS = {
    # BTG Pactual funds - these need to be verified
    "BTG-CREDCORP": None,  # Need to search for CNPJ
    "BTG-YIELD-DI": None,  # Need to search for CNPJ
}


if __name__ == "__main__":
    # Test: Search for BTG funds
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) > 1:
        pattern = sys.argv[1]
    else:
        pattern = "BTG PACTUAL"

    print(f"\nSearching for funds matching '{pattern}'...")
    results = search_fund_by_name(pattern)
    print(f"\nFound {len(results)} funds:")
    print(results.to_string())
