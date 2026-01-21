#!/usr/bin/env python3
"""
Batch import statements from local PDF files.

This script processes multiple PDF statements in chronological order,
uploading, parsing, and committing each one automatically.

Usage:
    python -m scripts.batch_import_statements --start-date 2022-11 --end-date 2025-12

Or to process all files:
    python -m scripts.batch_import_statements --all
"""

import argparse
import asyncio
import os
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent / "Extratos"
API_BASE_URL = os.getenv("API_BASE_URL", "https://investctr-production.up.railway.app")
ACCOUNT_ID = "42467b59-6465-4d10-9c89-43d1bb0eb387"  # BTG Pactual


def get_pdf_files(start_date: str | None = None, end_date: str | None = None) -> list[Path]:
    """
    Get list of PDF files to process, optionally filtered by date range.

    Args:
        start_date: Start month in format "YYYY-MM" (inclusive)
        end_date: End month in format "YYYY-MM" (inclusive)

    Returns:
        List of Path objects for PDF files in chronological order
    """
    pdf_files = []

    for year_dir in sorted(BASE_DIR.iterdir()):
        if not year_dir.is_dir():
            continue

        year = year_dir.name

        for pdf_file in sorted(year_dir.glob("*.pdf")):
            # Extract month from filename (format: MM-YYYY.pdf)
            filename = pdf_file.stem  # e.g., "11-2022"
            parts = filename.split("-")
            if len(parts) != 2:
                continue

            month, file_year = parts
            file_date = f"{file_year}-{month}"  # Convert to YYYY-MM format

            # Apply date filters
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            pdf_files.append(pdf_file)

    return pdf_files


async def get_auth_token() -> str:
    """
    Get authentication token.

    For now, this reads from environment variable.
    In production, this should use proper authentication.
    """
    token = os.getenv("AUTH_TOKEN")
    if not token:
        raise ValueError(
            "AUTH_TOKEN environment variable not set. "
            "Please set it with a valid JWT token."
        )
    return token


async def upload_document(
    client: httpx.AsyncClient,
    token: str,
    pdf_path: Path,
) -> str:
    """Upload a PDF document and return the document ID."""

    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        data = {"doc_type": "statement", "account_id": ACCOUNT_ID}

        response = await client.post(
            f"{API_BASE_URL}/api/v1/documents/upload",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
        )

    if response.status_code != 200:
        raise Exception(f"Upload failed: {response.status_code} - {response.text}")

    result = response.json()
    return result["id"]


async def parse_document(
    client: httpx.AsyncClient,
    token: str,
    document_id: str,
) -> dict:
    """Trigger parsing and wait for completion."""

    # Trigger parsing
    response = await client.post(
        f"{API_BASE_URL}/api/v1/documents/{document_id}/parse",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )

    if response.status_code not in (200, 202):
        raise Exception(f"Parse trigger failed: {response.status_code} - {response.text}")

    # Poll for completion
    max_attempts = 60  # 5 minutes max
    for attempt in range(max_attempts):
        await asyncio.sleep(5)

        response = await client.get(
            f"{API_BASE_URL}/api/v1/documents/{document_id}/parse",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

        if response.status_code != 200:
            continue

        result = response.json()
        status = result.get("status")

        if status == "completed":
            return result
        elif status == "failed":
            error = result.get("error", "Unknown error")
            raise Exception(f"Parsing failed: {error}")

        # Still processing, continue polling
        print(f"    Parsing... (attempt {attempt + 1}/{max_attempts})")

    raise Exception("Parsing timed out after 5 minutes")


async def commit_document(
    client: httpx.AsyncClient,
    token: str,
    document_id: str,
    parsed_data: dict,
) -> dict:
    """Commit parsed transactions to the database."""

    # Prepare commit payload
    data = parsed_data.get("data", {})

    commit_payload = {
        "account_id": ACCOUNT_ID,
        "transactions": data.get("transactions", []),
        "fixed_income": data.get("fixed_income_positions", []),
        "stock_lending": data.get("stock_lending", []),
        "cash_movements": data.get("cash_movements", []),
        "investment_funds": data.get("investment_funds", []),
    }

    response = await client.post(
        f"{API_BASE_URL}/api/v1/documents/{document_id}/commit",
        json=commit_payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )

    if response.status_code != 200:
        raise Exception(f"Commit failed: {response.status_code} - {response.text}")

    return response.json()


async def process_statement(
    client: httpx.AsyncClient,
    token: str,
    pdf_path: Path,
) -> dict:
    """Process a single statement: upload, parse, and commit."""

    print(f"\n{'='*60}")
    print(f"Processing: {pdf_path.name}")
    print(f"{'='*60}")

    # Step 1: Upload
    print("  [1/3] Uploading...")
    document_id = await upload_document(client, token, pdf_path)
    print(f"    Document ID: {document_id}")

    # Step 2: Parse
    print("  [2/3] Parsing with Claude AI...")
    parsed_data = await parse_document(client, token, document_id)

    transactions_count = len(parsed_data.get("data", {}).get("transactions", []))
    fixed_income_count = len(parsed_data.get("data", {}).get("fixed_income_positions", []))
    cash_movements_count = len(parsed_data.get("data", {}).get("cash_movements", []))

    print(f"    Found: {transactions_count} transactions, "
          f"{fixed_income_count} fixed income, "
          f"{cash_movements_count} cash movements")

    # Step 3: Commit
    print("  [3/3] Committing to database...")
    commit_result = await commit_document(client, token, document_id, parsed_data)

    print(f"    Created: {commit_result.get('transactions_created', 0)} transactions, "
          f"{commit_result.get('assets_created', 0)} assets, "
          f"{commit_result.get('fixed_income_created', 0)} fixed income")

    if commit_result.get("errors"):
        print(f"    Warnings: {commit_result['errors']}")

    return {
        "file": pdf_path.name,
        "document_id": document_id,
        "transactions_created": commit_result.get("transactions_created", 0),
        "assets_created": commit_result.get("assets_created", 0),
        "positions_updated": commit_result.get("positions_updated", 0),
    }


async def main():
    parser = argparse.ArgumentParser(description="Batch import PDF statements")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start month in YYYY-MM format (inclusive)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End month in YYYY-MM format (inclusive)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all PDF files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without processing",
    )

    args = parser.parse_args()

    # Determine date range
    start_date = args.start_date
    end_date = args.end_date

    if not args.all and not start_date:
        start_date = "2022-11"  # Default: start from after last imported

    # Get list of files to process
    pdf_files = get_pdf_files(start_date, end_date)

    print("=" * 70)
    print("BATCH IMPORT STATEMENTS")
    print("=" * 70)
    print(f"Source directory: {BASE_DIR}")
    print(f"Date range: {start_date or 'beginning'} to {end_date or 'end'}")
    print(f"Files to process: {len(pdf_files)}")
    print()

    if not pdf_files:
        print("No PDF files found matching criteria.")
        return

    # List files
    print("Files:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.relative_to(BASE_DIR)}")

    if args.dry_run:
        print("\n[DRY RUN] No files were processed.")
        return

    print()

    # Get auth token
    try:
        token = await get_auth_token()
    except ValueError as e:
        print(f"ERROR: {e}")
        print("\nTo get your auth token:")
        print("1. Open the app in your browser")
        print("2. Open Developer Tools (F12)")
        print("3. Go to Application > Local Storage")
        print("4. Copy the 'sb-...-auth-token' value")
        print("5. Set it: export AUTH_TOKEN='your-token-here'")
        return

    # Process files
    results = []
    errors = []

    async with httpx.AsyncClient() as client:
        for pdf_file in pdf_files:
            try:
                result = await process_statement(client, token, pdf_file)
                results.append(result)
            except Exception as e:
                error_msg = f"{pdf_file.name}: {str(e)}"
                print(f"\n  ERROR: {error_msg}")
                errors.append(error_msg)

                # Ask whether to continue
                # For automated runs, we continue by default
                continue

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Files processed successfully: {len(results)}")
    print(f"Files with errors: {len(errors)}")

    if results:
        total_transactions = sum(r.get("transactions_created", 0) for r in results)
        total_assets = sum(r.get("assets_created", 0) for r in results)
        print(f"Total transactions created: {total_transactions}")
        print(f"Total assets created: {total_assets}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Run quote backfill: python -m scripts.backfill_quotes")
    print("2. Run NAV backfill: python -m scripts.backfill_nav")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
