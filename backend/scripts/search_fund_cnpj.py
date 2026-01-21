#!/usr/bin/env python3
"""
Search for fund CNPJs in CVM database.

Usage:
    python scripts/search_fund_cnpj.py "BTG PACTUAL"
    python scripts/search_fund_cnpj.py "CREDCORP"
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.cvm_client import search_fund_by_name


def main():
    if len(sys.argv) > 1:
        pattern = " ".join(sys.argv[1:])
    else:
        pattern = "BTG PACTUAL"

    print(f"\nSearching for funds matching '{pattern}'...")
    print("=" * 80)

    results = search_fund_by_name(pattern)

    if results.empty:
        print("No funds found.")
        return

    print(f"\nFound {len(results)} funds:\n")

    # Show formatted results
    for _, row in results.head(50).iterrows():
        cnpj = row["CNPJ_FUNDO"]
        name = row["DENOM_SOCIAL"][:60]
        status = row["SIT"]
        print(f"CNPJ: {cnpj}")
        print(f"Nome: {name}")
        print(f"Status: {status}")
        print("-" * 80)

    if len(results) > 50:
        print(f"\n... and {len(results) - 50} more results")


if __name__ == "__main__":
    main()
